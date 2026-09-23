from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request

from app.auth.routes import authenticated_user, check_origin
from app.auth.users import User
from app.branches.repository import (
    BranchInUse,
    BranchNotFound,
    DuplicateBranchCode,
)
from app.branches.schemas import (
    BranchListResponse,
    BranchResponse,
    CreateBranch,
    UpdateBranch,
)
from app.branches.service import AccessDenied, BranchService


def branch_administrator(request: Request) -> User:
    actor, _ = authenticated_user(request)

    try:
        BranchService.authorize(actor)
    except AccessDenied:
        raise HTTPException(
            status_code=403,
            detail="No tienes permiso para gestionar sucursales.",
        ) from None

    return actor


router = APIRouter(
    prefix="/api/branches",
    tags=["branches"],
    dependencies=[Depends(branch_administrator)],
)

Actor = Annotated[User, Depends(branch_administrator)]
BranchId = UUID


def service(request: Request) -> BranchService:
    return BranchService(request.app.state.branches)


def handle_conflict(operation):
    try:
        return operation()
    except DuplicateBranchCode:
        raise HTTPException(
            status_code=409,
            detail="Ya existe una sucursal con ese código.",
        ) from None
    except BranchNotFound:
        raise HTTPException(
            status_code=404,
            detail="La sucursal no existe.",
        ) from None
    except BranchInUse:
        raise HTTPException(
            status_code=409,
            detail=(
                "No se puede desactivar la sucursal porque tiene "
                "usuarios activos asignados."
            ),
        ) from None
    except AccessDenied:
        raise HTTPException(
            status_code=403,
            detail="No tienes permiso para gestionar sucursales.",
        ) from None


@router.get("", response_model=BranchListResponse)
def list_branches(request: Request, actor: Actor):
    return {
        "branches": service(request).list_branches(actor),
    }


@router.post("", response_model=BranchResponse, status_code=201)
def create_branch(
    data: CreateBranch,
    request: Request,
    actor: Actor,
):
    check_origin(request)

    return handle_conflict(
        lambda: service(request).create(actor, data)
    )


@router.patch("/{branch_id}", response_model=BranchResponse)
def update_branch(
    branch_id: BranchId,
    data: UpdateBranch,
    request: Request,
    actor: Actor,
):
    check_origin(request)

    return handle_conflict(
        lambda: service(request).update(actor, branch_id, data)
    )


@router.post(
    "/{branch_id}/deactivate",
    response_model=BranchResponse,
)
def deactivate_branch(
    branch_id: BranchId,
    request: Request,
    actor: Actor,
):
    check_origin(request)

    return handle_conflict(
        lambda: service(request).deactivate(actor, branch_id)
    )