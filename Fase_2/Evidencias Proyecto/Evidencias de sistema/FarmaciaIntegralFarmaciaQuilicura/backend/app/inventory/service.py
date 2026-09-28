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
            or "inventario.consultar" not in actor.permissions
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


__all__ = [
    "AccessDenied",
    "InventoryLotAlreadyExists",
    "InventoryNotFound",
    "InventoryService",
]