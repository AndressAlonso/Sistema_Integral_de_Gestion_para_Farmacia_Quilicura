from datetime import date
from typing import Any
from uuid import UUID

from app.auth.users import User
from app.inventory.repository import (
    InventoryLotAlreadyExists,
    InventoryNotFound,
    PostgresInventoryRepository,
)
from app.inventory.schemas import (
    CreateInventoryLot,
    UpdateInventoryMinimum,
)


class AccessDenied(Exception):
    pass


class InvalidMovementDateRange(Exception):
    pass


class InvalidExpirationAlertDays(Exception):
    pass


class InventoryService:
    def __init__(
        self,
        repository: PostgresInventoryRepository,
    ):
        self.repository = repository

    @staticmethod
    def authorize(actor: User) -> None:
        if (
            not actor.is_active
            or "inventario.consultar"
            not in actor.permissions
        ):
            raise AccessDenied

    @staticmethod
    def authorize_lot_management(
        actor: User,
    ) -> None:
        if (
            not actor.is_active
            or "inventario.gestionar_lotes"
            not in actor.permissions
        ):
            raise AccessDenied

    @staticmethod
    def authorize_minimum_configuration(
        actor: User,
    ) -> None:
        if (
            not actor.is_active
            or "inventario.configurar_minimo"
            not in actor.permissions
        ):
            raise AccessDenied

    @staticmethod
    def validate_movement_date_range(
        start_date: date | None,
        end_date: date | None,
    ) -> None:
        if (
            start_date is not None
            and end_date is not None
            and start_date > end_date
        ):
            raise InvalidMovementDateRange

    @staticmethod
    def validate_expiration_alert_days(
        days: int,
    ) -> None:
        if days < 1 or days > 730:
            raise InvalidExpirationAlertDays

    def list_inventory(
        self,
        actor: User,
    ) -> list[dict[str, Any]]:
        self.authorize(actor)

        return self.repository.list_inventory()

    def update_minimum(
        self,
        actor: User,
        inventory_id: UUID,
        data: UpdateInventoryMinimum,
    ) -> dict[str, Any]:
        self.authorize_minimum_configuration(actor)

        return self.repository.update_minimum(
            inventory_id=inventory_id,
            minimum=data.minimum,
        )

    def list_lots(
        self,
        actor: User,
        inventory_id: UUID | None = None,
    ) -> list[dict[str, Any]]:
        self.authorize(actor)

        return self.repository.list_lots(
            inventory_id=inventory_id,
        )

    def create_lot(
        self,
        actor: User,
        data: CreateInventoryLot,
    ) -> dict[str, Any]:
        self.authorize_lot_management(actor)

        return self.repository.create_lot(
            inventory_id=data.inventory_id,
            lot_number=data.lot_number,
            expiration_date=data.expiration_date,
            quantity=data.quantity,
        )

    def list_movements(
        self,
        actor: User,
        inventory_id: UUID | None = None,
        product_id: UUID | None = None,
        branch_id: UUID | None = None,
        movement_type: str | None = None,
        start_date: date | None = None,
        end_date: date | None = None,
    ) -> list[dict[str, Any]]:
        self.authorize(actor)

        self.validate_movement_date_range(
            start_date=start_date,
            end_date=end_date,
        )

        normalized_type = None

        if movement_type is not None:
            normalized_type = movement_type.strip().upper()

            if not normalized_type:
                normalized_type = None

        return self.repository.list_movements(
            inventory_id=inventory_id,
            product_id=product_id,
            branch_id=branch_id,
            movement_type=normalized_type,
            start_date=start_date,
            end_date=end_date,
        )

    def list_expiration_alerts(
        self,
        actor: User,
        days: int,
        include_expired: bool = True,
        product_id: UUID | None = None,
        branch_id: UUID | None = None,
    ) -> list[dict[str, Any]]:
        self.authorize(actor)

        self.validate_expiration_alert_days(days)

        return self.repository.list_expiration_alerts(
            days=days,
            include_expired=include_expired,
            product_id=product_id,
            branch_id=branch_id,
        )


__all__ = [
    "AccessDenied",
    "InvalidExpirationAlertDays",
    "InvalidMovementDateRange",
    "InventoryLotAlreadyExists",
    "InventoryNotFound",
    "InventoryService",
]