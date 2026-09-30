from sqlalchemy import select, text
from sqlalchemy.dialects.postgresql import insert

from app.models import (
    InventarioSucursal,
    LoteInventario,
    Producto,
    RecepcionMercaderia,
    Sucursal,
)


class ReceiptRepository:
    def __init__(self, factory):
        self.factory = factory

    @staticmethod
    def lock_request(db, request_id):
        db.execute(text("SELECT pg_advisory_xact_lock(hashtextextended(:key, 0))"),
                   {"key": f"goods-receipt:{request_id}"})

    @staticmethod
    def receipt(db, receipt_id):
        return db.get(RecepcionMercaderia, receipt_id)

    @staticmethod
    def branch(db, branch_id):
        return db.scalar(select(Sucursal).where(Sucursal.id == branch_id)
                         .with_for_update(read=True))

    @staticmethod
    def product(db, product_id):
        return db.scalar(select(Producto).where(Producto.id == product_id)
                         .with_for_update(read=True))

    @staticmethod
    def inventory(db, product_id, branch_id):
        db.execute(insert(InventarioSucursal).values(
            producto_id=product_id, sucursal_id=branch_id,
            stock_fisico=0, stock_reservado=0, stock_minimo=0,
        ).on_conflict_do_nothing(constraint="uq_inventario_producto_sucursal"))
        return db.scalar(select(InventarioSucursal).where(
            InventarioSucursal.producto_id == product_id,
            InventarioSucursal.sucursal_id == branch_id,
        ).with_for_update(of=InventarioSucursal))

    @staticmethod
    def lot(db, inventory_id, number):
        return db.scalar(select(LoteInventario).where(
            LoteInventario.inventario_sucursal_id == inventory_id,
            LoteInventario.numero_lote == number,
        ).with_for_update(of=LoteInventario))

    @staticmethod
    def options(db, branch_id=None):
        branches = select(Sucursal).where(Sucursal.activa.is_(True))
        if branch_id is not None:
            branches = branches.where(Sucursal.id == branch_id)
        return {
            "products": [{"id": row.id, "name": row.nombre, "sku": row.sku}
                         for row in db.scalars(select(Producto).where(Producto.activo.is_(True))
                                               .order_by(Producto.nombre, Producto.id))],
            "branches": [{"id": row.id, "name": row.nombre}
                         for row in db.scalars(branches.order_by(Sucursal.nombre))],
        }

    @staticmethod
    def response(row):
        return {
            "id": row.id, "branch_id": row.sucursal_id, "user_id": row.usuario_id,
            "supplier": row.proveedor, "document_type": row.tipo_documento,
            "document_number": row.numero_documento, "document_date": row.fecha_documento,
            "created_at": row.creado_en,
            "items": [{
                "product_id": item.lote.inventario.producto_id,
                "lot_number": item.lote.numero_lote,
                "expiration_date": item.lote.fecha_vencimiento,
                "quantity": item.cantidad,
            } for item in row.detalles],
        }
