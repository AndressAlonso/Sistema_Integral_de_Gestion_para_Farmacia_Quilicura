from datetime import date
from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session, sessionmaker

from app.models import InventarioSucursal, LoteInventario


class InventoryNotFound(Exception):
    pass


class InventoryLotAlreadyExists(Exception):
    pass


class PostgresInventoryRepository:
    def __init__(
        self,
        session_factory: sessionmaker[Session],
    ):
        self.session_factory = session_factory

    @staticmethod
    def _inventory_record(
        record: InventarioSucursal,
    ) -> dict[str, Any]:
        return {
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

    @staticmethod
    def _lot_record(
        lot: LoteInventario,
    ) -> dict[str, Any]:
        inventory = lot.inventario

        return {
            "id": lot.id,
            "inventory_id": inventory.id,
            "product_id": inventory.producto_id,
            "product_name": inventory.producto.nombre,
            "product_sku": inventory.producto.sku,
            "branch_id": inventory.sucursal_id,
            "branch_name": inventory.sucursal.nombre,
            "branch_code": inventory.sucursal.codigo,
            "lot_number": lot.numero_lote,
            "expiration_date": lot.fecha_vencimiento,
            "quantity": lot.cantidad,
            "is_active": lot.activo,
            "created_at": lot.creado_en,
        }

    def list_inventory(self) -> list[dict[str, Any]]:
        with self.session_factory() as db:
            records = db.scalars(
                select(InventarioSucursal).order_by(
                    InventarioSucursal.producto_id,
                    InventarioSucursal.sucursal_id,
                )
            ).all()

            return [
                self._inventory_record(record)
                for record in records
            ]

    def list_lots(
        self,
        inventory_id: UUID | None = None,
    ) -> list[dict[str, Any]]:
        with self.session_factory() as db:
            query = select(LoteInventario)

            if inventory_id is not None:
                query = query.where(
                    LoteInventario.inventario_sucursal_id
                    == inventory_id
                )

            query = query.order_by(
                LoteInventario.fecha_vencimiento,
                LoteInventario.numero_lote,
                LoteInventario.id,
            )

            lots = db.scalars(query).all()

            return [
                self._lot_record(lot)
                for lot in lots
            ]

    def create_lot(
        self,
        inventory_id: UUID,
        lot_number: str,
        expiration_date: date,
        quantity: int,
    ) -> dict[str, Any]:
        normalized_lot_number = lot_number.strip()

        with self.session_factory() as db:
            inventory = db.get(
                InventarioSucursal,
                inventory_id,
            )

            if inventory is None:
                raise InventoryNotFound

            existing_lot = db.scalar(
                select(LoteInventario).where(
                    LoteInventario.inventario_sucursal_id
                    == inventory_id,
                    LoteInventario.numero_lote
                    == normalized_lot_number,
                )
            )

            if existing_lot is not None:
                raise InventoryLotAlreadyExists

            lot = LoteInventario(
                inventario_sucursal_id=inventory_id,
                numero_lote=normalized_lot_number,
                fecha_vencimiento=expiration_date,
                cantidad=quantity,
                activo=True,
            )

            db.add(lot)
            db.commit()
            db.refresh(lot)

            return self._lot_record(lot)