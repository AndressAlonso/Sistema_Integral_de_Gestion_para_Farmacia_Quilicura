from datetime import date, datetime, time, timedelta
from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session, sessionmaker

from app.models import (
    InventarioSucursal,
    LoteInventario,
    MovimientoInventario,
)


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
            "minimum": record.stock_minimo,
            "stock_status": record.estado_stock,
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

    @staticmethod
    def _movement_record(
        movement: MovimientoInventario,
    ) -> dict[str, Any]:
        inventory = movement.inventario

        return {
            "id": movement.id,
            "inventory_id": inventory.id,
            "product_id": inventory.producto_id,
            "product_name": inventory.producto.nombre,
            "product_sku": inventory.producto.sku,
            "branch_id": inventory.sucursal_id,
            "branch_name": inventory.sucursal.nombre,
            "branch_code": inventory.sucursal.codigo,
            "user_id": movement.usuario_id,
            "user_name": (
                movement.usuario.nombre
                if movement.usuario is not None
                else None
            ),
            "movement_type": movement.tipo,
            "physical_change": movement.cantidad_fisica,
            "reserved_change": movement.cantidad_reservada,
            "physical_before": (
                movement.stock_fisico_anterior
            ),
            "physical_after": (
                movement.stock_fisico_resultante
            ),
            "reserved_before": (
                movement.stock_reservado_anterior
            ),
            "reserved_after": (
                movement.stock_reservado_resultante
            ),
            "available_before": (
                movement.stock_disponible_anterior
            ),
            "available_after": (
                movement.stock_disponible_resultante
            ),
            "reason": movement.motivo,
            "reference_type": movement.referencia_tipo,
            "reference_id": movement.referencia_id,
            "created_at": movement.creado_en,
        }

    @staticmethod
    def _expiration_alert_record(
        lot: LoteInventario,
        today: date,
    ) -> dict[str, Any]:
        inventory = lot.inventario
        days_remaining = (
            lot.fecha_vencimiento - today
        ).days

        if days_remaining <= 0:
            alert_level = "VENCIDO"
        elif days_remaining <= 15:
            alert_level = "CRITICO"
        elif days_remaining <= 30:
            alert_level = "PROXIMO"
        else:
            alert_level = "SEGUIMIENTO"

        return {
            "lot_id": lot.id,
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
            "days_remaining": days_remaining,
            "alert_level": alert_level,
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

    def update_minimum(
        self,
        inventory_id: UUID,
        minimum: int,
    ) -> dict[str, Any]:
        with self.session_factory() as db:
            inventory = db.get(
                InventarioSucursal,
                inventory_id,
            )

            if inventory is None:
                raise InventoryNotFound

            inventory.stock_minimo = minimum

            db.commit()
            db.refresh(inventory)

            return self._inventory_record(inventory)

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

    def list_movements(
        self,
        inventory_id: UUID | None = None,
        product_id: UUID | None = None,
        branch_id: UUID | None = None,
        movement_type: str | None = None,
        start_date: date | None = None,
        end_date: date | None = None,
    ) -> list[dict[str, Any]]:
        with self.session_factory() as db:
            query = (
                select(MovimientoInventario)
                .join(
                    MovimientoInventario.inventario
                )
            )

            if inventory_id is not None:
                query = query.where(
                    MovimientoInventario
                    .inventario_sucursal_id
                    == inventory_id
                )

            if product_id is not None:
                query = query.where(
                    InventarioSucursal.producto_id
                    == product_id
                )

            if branch_id is not None:
                query = query.where(
                    InventarioSucursal.sucursal_id
                    == branch_id
                )

            if movement_type is not None:
                normalized_type = (
                    movement_type.strip().upper()
                )

                query = query.where(
                    MovimientoInventario.tipo
                    == normalized_type
                )

            if start_date is not None:
                start_datetime = datetime.combine(
                    start_date,
                    time.min,
                )

                query = query.where(
                    MovimientoInventario.creado_en
                    >= start_datetime
                )

            if end_date is not None:
                end_exclusive = datetime.combine(
                    end_date + timedelta(days=1),
                    time.min,
                )

                query = query.where(
                    MovimientoInventario.creado_en
                    < end_exclusive
                )

            query = query.order_by(
                MovimientoInventario.creado_en.desc(),
                MovimientoInventario.id.desc(),
            )

            movements = db.scalars(
                query
            ).unique().all()

            return [
                self._movement_record(movement)
                for movement in movements
            ]

    def list_expiration_alerts(
        self,
        days: int,
        include_expired: bool = True,
        product_id: UUID | None = None,
        branch_id: UUID | None = None,
        today: date | None = None,
    ) -> list[dict[str, Any]]:
        reference_date = today or date.today()
        maximum_date = (
            reference_date + timedelta(days=days)
        )

        with self.session_factory() as db:
            query = (
                select(LoteInventario)
                .join(LoteInventario.inventario)
                .where(
                    LoteInventario.activo.is_(True),
                    LoteInventario.cantidad > 0,
                    LoteInventario.fecha_vencimiento
                    <= maximum_date,
                )
            )

            if not include_expired:
                query = query.where(
                    LoteInventario.fecha_vencimiento
                    > reference_date
                )

            if product_id is not None:
                query = query.where(
                    InventarioSucursal.producto_id
                    == product_id
                )

            if branch_id is not None:
                query = query.where(
                    InventarioSucursal.sucursal_id
                    == branch_id
                )

            query = query.order_by(
                LoteInventario.fecha_vencimiento,
                LoteInventario.numero_lote,
                LoteInventario.id,
            )

            lots = db.scalars(
                query
            ).unique().all()

            return [
                self._expiration_alert_record(
                    lot,
                    reference_date,
                )
                for lot in lots
            ]