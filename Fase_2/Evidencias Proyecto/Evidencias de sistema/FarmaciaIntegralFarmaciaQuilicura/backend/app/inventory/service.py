from typing import Any

from app.auth.users import User
from app.inventory.repository import PostgresInventoryRepository


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

    def list_inventory(
        self,
        actor: User,
    ) -> list[dict[str, Any]]:
        self.authorize(actor)

        return self.repository.list_inventory()