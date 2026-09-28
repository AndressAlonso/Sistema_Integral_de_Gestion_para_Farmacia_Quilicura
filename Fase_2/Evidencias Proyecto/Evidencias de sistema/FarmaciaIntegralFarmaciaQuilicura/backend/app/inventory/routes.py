from typing import Annotated
from uuid import UUID

from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    Request,
)

from app.auth.routes import (
    authenticated_user,
    check_origin,
)
from app.auth.users import User
from app.inventory.schemas import (
    CreateInventoryLot,
    InventoryListResponse,
    InventoryLotListResponse,
    InventoryLotResponse,
    InventoryRecordResponse,
    UpdateInventoryMinimum,
)
from app.inventory.service import (
    AccessDenied,
    InventoryLotAlreadyExists,
    InventoryNotFound,
    InventoryService,
)


def inventory_reader(request: Request) -> User:
    actor, _ = authenticated_user(request)

    try:
        InventoryService.authorize(actor)
    except AccessDenied:
        raise HTTPException(
            status_code=403,
            detail=(
                "No tienes permiso para consultar "
                "el inventario."
            ),
        ) from None

    return actor


def lot_manager(request: Request) -> User:
    actor, _ = authenticated_user(request)

    try:
        InventoryService.authorize_lot_management(
            actor
        )
    except AccessDenied:
        raise HTTPException(
            status_code=403,
            detail=(
                "No tienes permiso para gestionar "
                "lotes de inventario."
            ),
        ) from None

    return actor


def minimum_manager(request: Request) -> User:
    actor, _ = authenticated_user(request)

    try:
        InventoryService.authorize_minimum_configuration(
            actor
        )
    except AccessDenied:
        raise HTTPException(
            status_code=403,
            detail=(
                "No tienes permiso para configurar "
                "el stock mínimo."
            ),
        ) from None

    return actor


router = APIRouter(
    prefix="/api/inventory",
    tags=["inventory"],
)


Reader = Annotated[
    User,
    Depends(inventory_reader),
]


LotManager = Annotated[
    User,
    Depends(lot_manager),
]


MinimumManager = Annotated[
    User,
    Depends(minimum_manager),
]


def service(request: Request) -> InventoryService:
    return InventoryService(
        request.app.state.inventory
    )


@router.get(
    "",
    response_model=InventoryListResponse,
)
def list_inventory(
    request: Request,
    actor: Reader,
):
    try:
        records = service(request).list_inventory(
            actor
        )
    except AccessDenied:
        raise HTTPException(
            status_code=403,
            detail=(
                "No tienes permiso para consultar "
                "el inventario."
            ),
        ) from None

    return {
        "records": records,
    }


@router.patch(
    "/{inventory_id}/minimum",
    response_model=InventoryRecordResponse,
)
def update_inventory_minimum(
    inventory_id: UUID,
    data: UpdateInventoryMinimum,
    request: Request,
    actor: MinimumManager,
):
    check_origin(request)

    try:
        return service(request).update_minimum(
            actor=actor,
            inventory_id=inventory_id,
            data=data,
        )
    except AccessDenied:
        raise HTTPException(
            status_code=403,
            detail=(
                "No tienes permiso para configurar "
                "el stock mínimo."
            ),
        ) from None
    except InventoryNotFound:
        raise HTTPException(
            status_code=404,
            detail=(
                "No existe el registro de inventario "
                "seleccionado."
            ),
        ) from None


@router.get(
    "/lots",
    response_model=InventoryLotListResponse,
)
def list_all_lots(
    request: Request,
    actor: Reader,
):
    try:
        lots = service(request).list_lots(
            actor
        )
    except AccessDenied:
        raise HTTPException(
            status_code=403,
            detail=(
                "No tienes permiso para consultar "
                "los lotes de inventario."
            ),
        ) from None

    return {
        "lots": lots,
    }


@router.post(
    "/lots",
    response_model=InventoryLotResponse,
    status_code=201,
)
def create_lot(
    data: CreateInventoryLot,
    request: Request,
    actor: LotManager,
):
    check_origin(request)

    try:
        return service(request).create_lot(
            actor,
            data,
        )
    except AccessDenied:
        raise HTTPException(
            status_code=403,
            detail=(
                "No tienes permiso para gestionar "
                "lotes de inventario."
            ),
        ) from None
    except InventoryNotFound:
        raise HTTPException(
            status_code=404,
            detail=(
                "No existe el registro de inventario "
                "seleccionado."
            ),
        ) from None
    except InventoryLotAlreadyExists:
        raise HTTPException(
            status_code=409,
            detail=(
                "Ya existe un lote con ese número para "
                "el producto y la sucursal seleccionados."
            ),
        ) from None


@router.get(
    "/{inventory_id}/lots",
    response_model=InventoryLotListResponse,
)
def list_inventory_lots(
    inventory_id: UUID,
    request: Request,
    actor: Reader,
):
    try:
        lots = service(request).list_lots(
            actor,
            inventory_id=inventory_id,
        )
    except AccessDenied:
        raise HTTPException(
            status_code=403,
            detail=(
                "No tienes permiso para consultar "
                "los lotes de inventario."
            ),
        ) from None

    return {
        "lots": lots,
    }