"""E4-H5: ajustes por lote atómicos, con reservas protegidas y reintentos seguros."""

from hashlib import sha256
from itertools import groupby

from app.models import AjusteInventario, AjusteInventarioDetalle, MovimientoInventario
from app.transfers.repository import TransferRepository

PERMISSION = "inventario.ajustar"
RECEIPT_PERMISSION = "inventario.registrar_entrada"


class AdjustmentError(Exception):
    def __init__(self, status, message):
        self.status, self.message = status, message
        super().__init__(message)


class AdjustmentService:
    def __init__(self, repository):
        self.repo = repository

    @staticmethod
    def can_adjust(actor):
        return (
            actor.is_active
            and PERMISSION in actor.permissions
            and bool({"ADMINISTRADOR", "ENCARGADO_INVENTARIO"}.intersection(actor.roles))
        )

    @staticmethod
    def authorize(actor, branch_id=None, options=False):
        allowed = AdjustmentService.can_adjust(actor) or (
            options and actor.is_active and RECEIPT_PERMISSION in actor.permissions
        )
        if not allowed:
            raise AdjustmentError(
                403, "No tienes permiso para esta operación de inventario."
            )
        if (
            branch_id is not None
            and branch_id != actor.branch_id
            and "ADMINISTRADOR" not in actor.roles
        ):
            raise AdjustmentError(
                403, "Solo puedes registrar movimientos en tu sucursal asignada."
            )

    def options(self, actor):
        self.authorize(actor, options=True)
        with self.repo.factory() as db:
            return self.repo.options(
                db, None if "ADMINISTRADOR" in actor.roles else actor.branch_id
            ) | {
                "can_receive": RECEIPT_PERMISSION in actor.permissions,
                "can_adjust": self.can_adjust(actor),
            }

    def get(self, actor, request_id):
        self.authorize(actor)
        with self.repo.factory() as db:
            row = self.repo.get(db, request_id)
            if row is None:
                raise AdjustmentError(404, "El ajuste no existe.")
            self.authorize(actor, row.sucursal_id)
            return self.repo.response(row)

    def create(self, actor, data):
        self.authorize(actor, data.branch_id)
        fingerprint = sha256(data.model_dump_json(exclude_none=True).encode()).hexdigest()
        with self.repo.factory.begin() as db:
            self.repo.lock_request(db, data.request_id)
            existing = self.repo.get(db, data.request_id)
            if existing:
                if (
                    existing.usuario_id != actor.id
                    or existing.solicitud_hash != fingerprint
                ):
                    raise AdjustmentError(
                        409, "El identificador ya fue utilizado con otros datos."
                    )
                return self.repo.response(existing), False
            branches = TransferRepository.branches(db, [data.branch_id])
            if not branches or not branches[0].activa:
                raise AdjustmentError(409, "La sucursal no existe o está inactiva.")
            lots = self.repo.lots(db, [item.lot_id for item in data.items])
            if len(lots) != len(data.items) or any(
                lot.inventario.sucursal_id != data.branch_id for lot in lots
            ):
                raise AdjustmentError(
                    409, "Selecciona lotes existentes de la sucursal indicada."
                )
            row = AjusteInventario(
                id=data.request_id,
                solicitud_hash=fingerprint,
                sucursal_id=data.branch_id,
                usuario_id=actor.id,
                motivo=data.reason,
            )
            db.add(row)
            items = {item.lot_id: item for item in data.items}
            lots.sort(key=lambda lot: (str(lot.inventario.producto_id), str(lot.id)))
            for product_id, group in groupby(
                lots, key=lambda lot: lot.inventario.producto_id
            ):
                # El ajuste corrige existencias físicas, incluso si su uso está bloqueado.
                product = TransferRepository.product(db, product_id)
                inv = TransferRepository.inventory(db, product_id, data.branch_id)
                reserved = TransferRepository.reserved_lots(db, inv.id)
                changes = []
                for old in group:
                    lot = self.repo.refresh_lot(db, old.id)
                    item = items[lot.id]
                    if item.expected_reserved is not None and item.expected_reserved != reserved.get(lot.id, 0):
                        raise AdjustmentError(409, "Las unidades disponibles cambiaron. Actualiza las existencias y revisa el ajuste.")
                    if lot.cantidad != item.expected_quantity:
                        raise AdjustmentError(
                            409,
                            "Un lote cambió. Actualiza las cantidades antes de guardar.",
                        )
                    if (not lot.activo or not product.activo) and item.new_quantity > lot.cantidad:
                        raise AdjustmentError(409, "Un lote o producto deshabilitado solo admite reducir sus unidades mediante un ajuste.")
                    if item.new_quantity < reserved.get(lot.id, 0):
                        raise AdjustmentError(
                            409,
                            f"El lote {lot.numero_lote} tiene {reserved[lot.id]} unidades "
                            "reservadas para pedidos o transferencias. "
                            f"La cantidad final no puede ser menor que {reserved[lot.id]}. "
                            "El ajuste no se guardó.",
                        )
                    changes.append((lot, item))
                final = inv.stock_fisico + sum(
                    item.new_quantity - lot.cantidad for lot, item in changes
                )
                if final < inv.stock_reservado or final < 0 or final > 2_147_483_647:
                    raise AdjustmentError(
                        409,
                        "El ajuste deja stock insuficiente para las reservas o supera el límite admitido. "
                        f"Este producto tiene {inv.stock_reservado} unidades reservadas en la sucursal; "
                        "el stock físico total debe cubrirlas. El ajuste no se guardó.",
                    )
                # Aumentos primero para respetar reservas durante cada movimiento.
                changes.sort(
                    key=lambda change: change[1].new_quantity - change[0].cantidad,
                    reverse=True,
                )
                for lot, item in changes:
                    before = lot.cantidad
                    difference = item.new_quantity - before
                    if inv.stock_fisico + difference > 2_147_483_647:
                        raise AdjustmentError(
                            409, "El saldo intermedio supera el límite admitido."
                        )
                    db.add(
                        AjusteInventarioDetalle(
                            ajuste_id=row.id,
                            lote_id=lot.id,
                            cantidad_anterior=before,
                            cantidad_nueva=item.new_quantity,
                        )
                    )
                    db.add(
                        MovimientoInventario(
                            inventario_sucursal_id=inv.id,
                            usuario_id=actor.id,
                            tipo="AJUSTE",
                            cantidad_fisica=difference,
                            cantidad_reservada=0,
                            stock_fisico_anterior=inv.stock_fisico,
                            stock_fisico_resultante=inv.stock_fisico + difference,
                            stock_reservado_anterior=inv.stock_reservado,
                            stock_reservado_resultante=inv.stock_reservado,
                            motivo=data.reason,
                            referencia_tipo="AJUSTE_INVENTARIO",
                            referencia_id=row.id,
                        )
                    )
                    lot.cantidad = item.new_quantity
                    inv.stock_fisico += difference
            db.flush()
            return self.repo.response(row), True
