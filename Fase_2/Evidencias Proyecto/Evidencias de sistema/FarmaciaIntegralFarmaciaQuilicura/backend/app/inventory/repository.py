from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session, sessionmaker

from app.models import InventarioSucursal


class PostgresInventoryRepository:
    def __init__(
        self,
        session_factory: sessionmaker[Session],
    ):
        self.session_factory = session_factory

    def list_inventory(self) -> list[dict[str, Any]]:
        with self.session_factory() as db:
            records = db.scalars(
                select(InventarioSucursal).order_by(
                    InventarioSucursal.producto_id,
                    InventarioSucursal.sucursal_id,
                )
            ).all()

            return [
                {
                    "id": record.id,
                    "product_id": record.producto_id,
                    "product_name": record.producto.nombre,
                    "product_sku": record.producto.sku,
                    "branch_id": record.sucursal_id,
                    "branch_name": record.sucursal.nombre,
                    "branch_code": record.sucursal.codigo,
                    "physical": record.stock_fisico,
                    "reserved": record.stock_reservado,
                    "available": record.stock_disponible,
                }
                for record in records
            ]