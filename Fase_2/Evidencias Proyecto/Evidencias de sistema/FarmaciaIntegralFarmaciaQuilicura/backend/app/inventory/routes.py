from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request

from app.auth.routes import authenticated_user
from app.auth.users import User
from app.inventory.schemas import InventoryListResponse
from app.inventory.service import (
    AccessDenied,
    InventoryService,
)


def inventory_reader(request: Request) -> User:
    actor, _ = authenticated_user(request)

    try:
        InventoryService.authorize(actor)
    except AccessDenied:
        raise HTTPException(
            status_code=403,
            detail="No tienes permiso para consultar el inventario.",
        ) from None

    return actor


router = APIRouter(
    prefix="/api/inventory",
    tags=["inventory"],
    dependencies=[Depends(inventory_reader)],
)

Actor = Annotated[User, Depends(inventory_reader)]


def service(request: Request) -> InventoryService:
    return InventoryService(request.app.state.inventory)


@router.get(
    "",
    response_model=InventoryListResponse,
)
def list_inventory(
    request: Request,
    actor: Actor,
):
    try:
        records = service(request).list_inventory(actor)
    except AccessDenied:
        raise HTTPException(
            status_code=403,
            detail="No tienes permiso para consultar el inventario.",
        ) from None

    return {
        "records": records,
    }