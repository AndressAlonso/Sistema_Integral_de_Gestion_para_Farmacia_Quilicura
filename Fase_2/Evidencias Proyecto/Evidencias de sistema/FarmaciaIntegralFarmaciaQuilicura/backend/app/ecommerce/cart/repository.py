from sqlalchemy import func, select, text

from app.models import (
    InventarioSucursal,
    LoteInventario,
    Producto,
    Sucursal,
    Transferencia,
    TransferenciaDetalle,
    TransferenciaLote,
)


class CartRepository:
    def __init__(self, factory):
        self.factory = factory

    def snapshot(self, product_ids):
        with self.factory() as db:
            # Una sola instantánea consistente; además PostgreSQL prohíbe escrituras.
            if not db.connection().in_nested_transaction():
                db.execute(text("SET TRANSACTION ISOLATION LEVEL REPEATABLE READ, READ ONLY"))
            today = db.scalar(select(func.current_date()))
            branches = list(db.scalars(select(Sucursal).where(Sucursal.activa.is_(True))))
            products = list(db.scalars(select(Producto).where(Producto.id.in_(product_ids))))
            inventories = list(db.scalars(select(InventarioSucursal).where(
                InventarioSucursal.producto_id.in_(product_ids),
                InventarioSucursal.sucursal_id.in_([b.id for b in branches]),
            )))
            inventory_ids = [row.id for row in inventories]
            lots = list(db.scalars(select(LoteInventario).where(LoteInventario.inventario_sucursal_id.in_(inventory_ids))))
            reservations = dict(db.execute(select(
                TransferenciaLote.lote_origen_id, func.sum(TransferenciaLote.cantidad),
            ).join(TransferenciaDetalle, TransferenciaDetalle.id == TransferenciaLote.detalle_id)
                .join(Transferencia, Transferencia.id == TransferenciaDetalle.transferencia_id)
                .join(LoteInventario, LoteInventario.id == TransferenciaLote.lote_origen_id)
                .where(Transferencia.estado.in_(("SOLICITADA", "AUTORIZADA")),
                       LoteInventario.inventario_sucursal_id.in_(inventory_ids))
                .group_by(TransferenciaLote.lote_origen_id)).all())
            return today, branches, products, inventories, lots, reservations
