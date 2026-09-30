from sqlalchemy import func, or_, select, text
from sqlalchemy.dialects.postgresql import insert

from app.models import (
    InventarioSucursal,
    LoteInventario,
    MovimientoInventario,
    Producto,
    Sucursal,
    Transferencia,
    TransferenciaDetalle,
    TransferenciaLote,
    UsuarioInterno,
)

RESERVED_STATES = ("SOLICITADA", "AUTORIZADA")
PENDING_STATES = (*RESERVED_STATES, "EN_TRANSITO")


class TransferRepository:
    def __init__(self, factory):
        self.factory = factory

    @staticmethod
    def lock_request(db, request_id):
        db.execute(
            text("SELECT pg_advisory_xact_lock(hashtextextended(:key, 0))"),
            {"key": f"transfer:{request_id}"},
        )

    @staticmethod
    def branches(db, ids):
        return list(
            db.scalars(
                select(Sucursal)
                .where(Sucursal.id.in_(ids))
                .order_by(Sucursal.id)
                .with_for_update(read=True)
            )
        )

    @staticmethod
    def get(db, transfer_id, lock=False):
        query = select(Transferencia).where(Transferencia.id == transfer_id)
        if lock:
            query = query.with_for_update().execution_options(populate_existing=True)
        return db.scalar(query)

    @staticmethod
    def inventory(db, product_id, branch_id, create=False):
        if create:
            db.execute(
                insert(InventarioSucursal)
                .values(
                    producto_id=product_id,
                    sucursal_id=branch_id,
                    stock_fisico=0,
                    stock_reservado=0,
                    stock_minimo=0,
                )
                .on_conflict_do_nothing(constraint="uq_inventario_producto_sucursal")
            )
        return db.scalar(
            select(InventarioSucursal)
            .where(
                InventarioSucursal.producto_id == product_id,
                InventarioSucursal.sucursal_id == branch_id,
            )
            .with_for_update(of=InventarioSucursal)
            .execution_options(populate_existing=True)
        )

    @staticmethod
    def product(db, product_id):
        return db.scalar(
            select(Producto).where(Producto.id == product_id).with_for_update(read=True)
        )

    @staticmethod
    def lots(db, inventory_id, today):
        return list(
            db.scalars(
                select(LoteInventario)
                .where(
                    LoteInventario.inventario_sucursal_id == inventory_id,
                    LoteInventario.activo.is_(True),
                    LoteInventario.cantidad > 0,
                    LoteInventario.fecha_vencimiento > today,
                )
                .order_by(LoteInventario.fecha_vencimiento, LoteInventario.id)
            )
        )

    @staticmethod
    def reserved_lots(db, inventory_id):
        return dict(
            db.execute(
                select(
                    TransferenciaLote.lote_origen_id,
                    func.sum(TransferenciaLote.cantidad),
                )
                .join(
                    TransferenciaDetalle,
                    TransferenciaDetalle.id == TransferenciaLote.detalle_id,
                )
                .join(
                    Transferencia,
                    Transferencia.id == TransferenciaDetalle.transferencia_id,
                )
                .join(
                    LoteInventario,
                    LoteInventario.id == TransferenciaLote.lote_origen_id,
                )
                .where(
                    Transferencia.estado.in_(RESERVED_STATES),
                    LoteInventario.inventario_sucursal_id == inventory_id,
                )
                .group_by(TransferenciaLote.lote_origen_id)
            ).all()
        )

    @staticmethod
    def destination_lot(db, inventory_id, source):
        return db.scalar(
            select(LoteInventario)
            .where(
                LoteInventario.inventario_sucursal_id == inventory_id,
                LoteInventario.numero_lote == source.numero_lote,
            )
            .with_for_update(of=LoteInventario)
        )

    @staticmethod
    def movement(db, row, actor, transfer_id, physical, reserved, kind):
        db.add(
            MovimientoInventario(
                inventario_sucursal_id=row.id,
                usuario_id=actor.id,
                tipo=kind,
                cantidad_fisica=physical,
                cantidad_reservada=reserved,
                stock_fisico_anterior=row.stock_fisico,
                stock_fisico_resultante=row.stock_fisico + physical,
                stock_reservado_anterior=row.stock_reservado,
                stock_reservado_resultante=row.stock_reservado + reserved,
                motivo=f"Transferencia {transfer_id}",
                referencia_tipo="TRANSFERENCIA",
                referencia_id=transfer_id,
            )
        )
        row.stock_fisico += physical
        row.stock_reservado += reserved

    @staticmethod
    def visible_query(actor):
        query = select(Transferencia)
        if "ADMINISTRADOR" not in actor.roles:
            query = query.where(
                or_(
                    Transferencia.origen_id == actor.branch_id,
                    Transferencia.destino_id == actor.branch_id,
                )
            )
        return query.order_by(Transferencia.solicitada_en.desc(), Transferencia.id)

    @staticmethod
    def public(row, actor):
        admin = "ADMINISTRADOR" in actor.roles
        permissions = actor.permissions
        actions = []
        if admin and "transferencias.autorizar" in permissions:
            if row.estado == "SOLICITADA":
                actions.append("approve")
            if row.estado in RESERVED_STATES:
                actions.append("reject")
        if (
            row.estado == "AUTORIZADA"
            and (admin or row.origen_id == actor.branch_id)
            and "transferencias.despachar" in permissions
        ):
            actions.append("dispatch")
        if (
            row.estado == "EN_TRANSITO"
            and (admin or row.destino_id == actor.branch_id)
            and "transferencias.recibir" in permissions
        ):
            actions.append("receive")
        return {
            "id": row.id,
            "origin_id": row.origen_id,
            "origin_name": row.origen.nombre,
            "destination_id": row.destino_id,
            "destination_name": row.destino.nombre,
            "state": row.estado,
            "created_at": row.solicitada_en,
            "requested_by": row.solicitante.nombre,
            "items": [
                {
                    "product_id": item.producto_id,
                    "product_name": item.producto.nombre,
                    "sku": item.producto.sku,
                    "quantity": item.cantidad,
                    "lots": [
                        {
                            "number": allocation.lote_origen.numero_lote,
                            "expiration_date": allocation.lote_origen.fecha_vencimiento,
                            "quantity": allocation.cantidad,
                        }
                        for allocation in item.lotes
                    ],
                }
                for item in row.detalles
            ],
            "rejection_reason": row.motivo_rechazo,
            "actions": actions,
        }

    @staticmethod
    def timeline(db, row):
        result = []
        for event, timestamp, user_id in (
            ("Solicitada", row.solicitada_en, row.solicitante_id),
            ("Autorizada", row.autorizada_en, row.autorizador_id),
            ("Despachada / en tránsito", row.despachada_en, row.despachador_id),
            ("Recibida", row.recibida_en, row.receptor_id),
            ("Rechazada", row.rechazada_en, row.rechazada_por_id),
        ):
            if timestamp:
                user = db.get(UsuarioInterno, user_id)
                result.append({"event": event, "at": timestamp, "user": user.nombre})
        return result
