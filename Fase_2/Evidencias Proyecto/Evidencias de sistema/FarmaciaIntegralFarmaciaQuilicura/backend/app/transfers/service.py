"""E4-H1/H2/H3: transiciones transaccionales con reservas FEFO y recepción total."""

from datetime import datetime, timezone
from hashlib import sha256

from sqlalchemy import select

from app.models import (
    InventarioSucursal,
    LoteInventario,
    Sucursal,
    Transferencia,
    TransferenciaDetalle,
    TransferenciaLote,
)
from app.transfers.repository import RESERVED_STATES


class TransferError(Exception):
    def __init__(self, status, message):
        self.status, self.message = status, message
        super().__init__(message)


class TransferService:
    def __init__(self, repository):
        self.repo = repository

    @staticmethod
    def authorize(actor, action="consultar"):
        if (
            not actor.is_active
            or "transferencias.consultar" not in actor.permissions
            or f"transferencias.{action}" not in actor.permissions
        ):
            raise TransferError(
                403, "No tienes permiso para esta operación de transferencias."
            )
        if action == "autorizar" and "ADMINISTRADOR" not in actor.roles:
            raise TransferError(
                403, "Solo un administrador puede autorizar o rechazar transferencias."
            )

    @staticmethod
    def check_scope(actor, row):
        if "ADMINISTRADOR" not in actor.roles and actor.branch_id not in (
            row.origen_id,
            row.destino_id,
        ):
            raise TransferError(403, "La transferencia no corresponde a tu sucursal.")

    def response(self, db, row, actor):
        return self.repo.public(row, actor) | {"timeline": self.repo.timeline(db, row)}

    def options(self, actor):
        self.authorize(actor)
        today = datetime.now(timezone.utc).date()
        with self.repo.factory() as db:
            branches = [
                {"id": b.id, "name": b.nombre}
                for b in db.scalars(
                    select(Sucursal)
                    .where(Sucursal.activa.is_(True))
                    .order_by(Sucursal.nombre)
                )
            ]
            query = select(InventarioSucursal)
            if "ADMINISTRADOR" not in actor.roles:
                query = query.where(InventarioSucursal.sucursal_id == actor.branch_id)
            stock = []
            for inv in db.scalars(query):
                if not inv.producto.activo or not inv.sucursal.activa:
                    continue
                reserved = self.repo.reserved_lots(db, inv.id)
                lot_units = sum(
                    max(0, lot.cantidad - reserved.get(lot.id, 0))
                    for lot in self.repo.lots(db, inv.id, today)
                )
                stock.append(
                    {
                        "product_id": inv.producto_id,
                        "product_name": inv.producto.nombre,
                        "sku": inv.producto.sku,
                        "branch_id": inv.sucursal_id,
                        "available": min(inv.stock_disponible, lot_units),
                    }
                )
            return {
                "branches": branches,
                "stock": stock,
                "can_create": "transferencias.solicitar" in actor.permissions,
                "origin_ids": [
                    b["id"]
                    for b in branches
                    if "ADMINISTRADOR" in actor.roles or b["id"] == actor.branch_id
                ],
            }

    def list(self, actor):
        self.authorize(actor)
        with self.repo.factory() as db:
            return {
                "transfers": [
                    self.response(db, row, actor)
                    for row in db.scalars(self.repo.visible_query(actor))
                ]
            }

    def get(self, actor, transfer_id):
        self.authorize(actor)
        with self.repo.factory() as db:
            row = self.repo.get(db, transfer_id)
            if row is None:
                raise TransferError(404, "La transferencia no existe.")
            self.check_scope(actor, row)
            return self.response(db, row, actor)

    def create(self, actor, data):
        self.authorize(actor, "solicitar")
        if "ADMINISTRADOR" not in actor.roles and actor.branch_id != data.origin_id:
            raise TransferError(
                403, "Solo puedes solicitar desde tu sucursal asignada."
            )
        fingerprint = sha256(data.model_dump_json().encode()).hexdigest()
        today = datetime.now(timezone.utc).date()
        with self.repo.factory.begin() as db:
            self.repo.lock_request(db, data.request_id)
            existing = self.repo.get(db, data.request_id)
            if existing:
                if (
                    existing.solicitante_id != actor.id
                    or existing.solicitud_hash != fingerprint
                ):
                    raise TransferError(
                        409, "El identificador de solicitud ya tiene otros datos."
                    )
                return self.response(db, existing, actor), False
            branches = self.repo.branches(db, [data.origin_id, data.destination_id])
            if len(branches) != 2 or not all(b.activa for b in branches):
                raise TransferError(
                    409, "Selecciona dos sucursales activas y distintas."
                )
            row = Transferencia(
                id=data.request_id,
                solicitud_hash=fingerprint,
                origen_id=data.origin_id,
                destino_id=data.destination_id,
                estado="SOLICITADA",
                solicitante_id=actor.id,
            )
            db.add(row)
            for item in sorted(data.items, key=lambda i: str(i.product_id)):
                product = self.repo.product(db, item.product_id)
                if product is None or not product.activo:
                    raise TransferError(409, "Un producto no existe o está inactivo.")
                inv = self.repo.inventory(db, item.product_id, data.origin_id)
                if inv is None or inv.stock_disponible < item.quantity:
                    raise TransferError(
                        409,
                        "Stock disponible insuficiente en origen. Actualiza y revisa las cantidades.",
                    )
                detail = TransferenciaDetalle(
                    transferencia_id=row.id,
                    producto_id=item.product_id,
                    cantidad=item.quantity,
                )
                db.add(detail)
                db.flush()
                reservations = self.repo.reserved_lots(db, inv.id)
                remaining = item.quantity
                for lot in self.repo.lots(db, inv.id, today):
                    take = min(
                        remaining, max(0, lot.cantidad - reservations.get(lot.id, 0))
                    )
                    if take:
                        db.add(
                            TransferenciaLote(
                                detalle_id=detail.id,
                                lote_origen_id=lot.id,
                                cantidad=take,
                            )
                        )
                        remaining -= take
                    if remaining == 0:
                        break
                if remaining:
                    raise TransferError(
                        409,
                        "No hay suficientes unidades en lotes activos, vigentes y sin reservar.",
                    )
                self.repo.movement(db, inv, actor, row.id, 0, item.quantity, "RESERVA")
            db.flush()
            return self.response(db, row, actor), True

    def change(self, actor, transfer_id, action, data=None):
        permission = {
            "approve": "autorizar",
            "reject": "autorizar",
            "dispatch": "despachar",
            "receive": "recibir",
        }[action]
        self.authorize(actor, permission)
        now = datetime.now(timezone.utc)
        with self.repo.factory.begin() as db:
            row = self.repo.get(db, transfer_id)
            if row is None:
                raise TransferError(404, "La transferencia no existe.")
            self.check_scope(actor, row)
            # Bloqueo de sucursales antes de la transferencia: coordina con desactivación.
            branches = self.repo.branches(db, [row.origen_id, row.destino_id])
            row = self.repo.get(db, transfer_id, lock=True)
            admin = "ADMINISTRADOR" in actor.roles
            if action == "dispatch" and not admin and actor.branch_id != row.origen_id:
                raise TransferError(
                    403, "El despacho debe confirmarse desde la sucursal origen."
                )
            if action == "receive" and not admin and actor.branch_id != row.destino_id:
                raise TransferError(
                    403, "La recepción debe confirmarse desde la sucursal destino."
                )
            if action == "receive":
                actual = {item.product_id: item.quantity for item in data.items}
                expected = {item.producto_id: item.cantidad for item in row.detalles}
                if len(actual) != len(data.items) or actual != expected:
                    raise TransferError(
                        409,
                        "Las cantidades recibidas deben coincidir completamente con el despacho. La transferencia continúa en tránsito.",
                    )
            target = {
                "approve": "AUTORIZADA",
                "reject": "RECHAZADA",
                "dispatch": "EN_TRANSITO",
                "receive": "RECIBIDA",
            }[action]
            if row.estado == target:
                return self.response(db, row, actor)
            expected_states = {
                "approve": ("SOLICITADA",),
                "reject": RESERVED_STATES,
                "dispatch": ("AUTORIZADA",),
                "receive": ("EN_TRANSITO",),
            }
            if row.estado not in expected_states[action]:
                raise TransferError(
                    409,
                    "El estado cambió o no permite esta acción. Actualiza el listado.",
                )
            if action != "reject" and not all(b.activa for b in branches):
                raise TransferError(
                    409, "Las sucursales deben estar activas para continuar."
                )
            if action == "approve":
                row.autorizador_id, row.autorizada_en = actor.id, now
            elif action == "reject":
                for detail in row.detalles:
                    inv = self.repo.inventory(db, detail.producto_id, row.origen_id)
                    if inv is None or inv.stock_reservado < detail.cantidad:
                        raise TransferError(
                            409,
                            "La reserva no coincide con inventario; requiere revisión.",
                        )
                    self.repo.movement(
                        db,
                        inv,
                        actor,
                        row.id,
                        0,
                        -detail.cantidad,
                        "LIBERACION_RESERVA",
                    )
                row.rechazada_por_id, row.rechazada_en, row.motivo_rechazo = (
                    actor.id,
                    now,
                    data.reason,
                )
            elif action == "dispatch":
                self.dispatch(db, row, actor, now.date())
                row.despachador_id, row.despachada_en = actor.id, now
            else:
                self.receive(db, row, actor)
                row.receptor_id, row.recibida_en = actor.id, now
            row.estado = target
            db.flush()
            return self.response(db, row, actor)

    def dispatch(self, db, row, actor, today):
        for detail in row.detalles:
            product = self.repo.product(db, detail.producto_id)
            if not product.activo:
                raise TransferError(
                    409, "Un producto está inactivo; revisa o rechaza la solicitud."
                )
            inv = self.repo.inventory(db, detail.producto_id, row.origen_id)
            if (
                inv is None
                or inv.stock_fisico < detail.cantidad
                or inv.stock_reservado < detail.cantidad
            ):
                raise TransferError(409, "La reserva no coincide con el stock físico.")
            for allocation in detail.lotes:
                lot = allocation.lote_origen
                if (
                    not lot.activo
                    or lot.fecha_vencimiento <= today
                    or lot.cantidad < allocation.cantidad
                ):
                    raise TransferError(
                        409,
                        "Un lote reservado ya no está disponible o venció; rechaza la solicitud para liberar su reserva.",
                    )
                lot.cantidad -= allocation.cantidad
            self.repo.movement(
                db,
                inv,
                actor,
                row.id,
                -detail.cantidad,
                -detail.cantidad,
                "TRANSFERENCIA_SALIDA",
            )

    def receive(self, db, row, actor):
        for detail in row.detalles:
            inv = self.repo.inventory(
                db, detail.producto_id, row.destino_id, create=True
            )
            if inv.stock_fisico + detail.cantidad > 2_147_483_647:
                raise TransferError(
                    409, "El inventario destino supera el límite admitido."
                )
            for allocation in detail.lotes:
                source = allocation.lote_origen
                lot = self.repo.destination_lot(db, inv.id, source)
                if lot and (
                    not lot.activo or lot.fecha_vencimiento != source.fecha_vencimiento
                ):
                    raise TransferError(
                        409,
                        "El lote destino está inactivo o tiene otro vencimiento; requiere revisión.",
                    )
                if lot is None:
                    lot = LoteInventario(
                        inventario_sucursal_id=inv.id,
                        numero_lote=source.numero_lote,
                        fecha_vencimiento=source.fecha_vencimiento,
                        cantidad=0,
                        activo=True,
                    )
                    db.add(lot)
                if lot.cantidad + allocation.cantidad > 2_147_483_647:
                    raise TransferError(
                        409, "El lote destino supera el límite admitido."
                    )
                lot.cantidad += allocation.cantidad
                db.flush()
                allocation.lote_destino_id = lot.id
            self.repo.movement(
                db, inv, actor, row.id, detail.cantidad, 0, "TRANSFERENCIA_ENTRADA"
            )
