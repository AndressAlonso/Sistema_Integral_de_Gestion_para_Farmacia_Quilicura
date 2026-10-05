from sqlalchemy import select, text

from app.models import (
    AjusteInventario,
    InventarioSucursal,
    LoteInventario,
    Producto,
    Sucursal,
)


class AdjustmentRepository:
    def __init__(self, factory):
        self.factory = factory

    @staticmethod
    def lock_request(db, request_id):
        db.execute(
            text("SELECT pg_advisory_xact_lock(hashtextextended(:key, 0))"),
            {"key": f"inventory-adjustment:{request_id}"},
        )

    @staticmethod
    def get(db, request_id):
        return db.get(AjusteInventario, request_id)

    @staticmethod
    def lots(db, ids):
        return list(
            db.scalars(select(LoteInventario).where(LoteInventario.id.in_(ids)))
        )

    @staticmethod
    def refresh_lot(db, lot_id):
        return db.scalar(
            select(LoteInventario)
            .where(LoteInventario.id == lot_id)
            .with_for_update(of=LoteInventario)
            .execution_options(populate_existing=True)
        )

    @staticmethod
    def options(db, branch_id):
        branches = select(Sucursal).where(Sucursal.activa.is_(True))
        query = (
            select(LoteInventario)
            .join(InventarioSucursal)
            .join(Producto)
            .join(Sucursal, Sucursal.id == InventarioSucursal.sucursal_id)
            .where(
                LoteInventario.activo.is_(True),
                Producto.activo.is_(True),
                Sucursal.activa.is_(True),
            )
        )
        if branch_id is not None:
            branches = branches.where(Sucursal.id == branch_id)
            query = query.where(InventarioSucursal.sucursal_id == branch_id)
        return {
            "products": [
                {
                    "id": inventory.producto_id,
                    "name": inventory.producto.nombre,
                    "sku": inventory.producto.sku,
                    "branch_id": inventory.sucursal_id,
                    "quantity": inventory.stock_fisico,
                }
                for inventory in db.scalars(
                    select(InventarioSucursal).join(Producto).join(Sucursal)
                    .where(Producto.activo.is_(True), Sucursal.activa.is_(True))
                    .where(True if branch_id is None else InventarioSucursal.sucursal_id == branch_id)
                    .order_by(Producto.nombre, InventarioSucursal.id)
                )
            ],
            "branches": [
                {"id": row.id, "name": row.nombre}
                for row in db.scalars(branches.order_by(Sucursal.nombre))
            ],
            "lots": [
                {
                    "id": row.id,
                    "product_id": row.inventario.producto_id,
                    "product_name": row.inventario.producto.nombre,
                    "sku": row.inventario.producto.sku,
                    "branch_id": row.inventario.sucursal_id,
                    "number": row.numero_lote,
                    "expiration_date": row.fecha_vencimiento,
                    "quantity": row.cantidad,
                }
                for row in db.scalars(
                    query.order_by(
                        Producto.nombre,
                        LoteInventario.fecha_vencimiento,
                        LoteInventario.id,
                    )
                )
            ],
        }

    @staticmethod
    def response(row):
        return {
            "id": row.id,
            "branch_id": row.sucursal_id,
            "user_id": row.usuario_id,
            "reason": row.motivo,
            "created_at": row.creado_en,
            "items": [
                {
                    "lot_id": item.lote_id,
                    "lot_number": item.lote.numero_lote,
                    "product_id": item.lote.inventario.producto_id,
                    "product_name": item.lote.inventario.producto.nombre,
                    "previous_quantity": item.cantidad_anterior,
                    "new_quantity": item.cantidad_nueva,
                    "difference": item.cantidad_nueva - item.cantidad_anterior,
                }
                for item in row.detalles
            ],
        }
