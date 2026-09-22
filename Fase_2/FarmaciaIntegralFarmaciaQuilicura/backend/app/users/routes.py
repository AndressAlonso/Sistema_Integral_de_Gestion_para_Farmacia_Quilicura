from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request

from app.auth.routes import authenticated_user, check_origin
from app.auth.users import DuplicateEmail, InvalidReference, User, UserNotFound
from app.users.schemas import CreateUser, UpdateUser, UserListResponse, UserResponse
from app.users.service import AccessDenied, UserService


def administrator(request: Request) -> User:
    actor, _ = authenticated_user(request)
    try:
        UserService.authorize(actor)
    except AccessDenied:
        raise HTTPException(403, "No tienes permiso para gestionar usuarios.") from None
    return actor


router = APIRouter(
    prefix="/api/users", tags=["users"], dependencies=[Depends(administrator)]
)
Actor = Annotated[User, Depends(administrator)]
UserId = UUID


def service(request: Request) -> UserService:
    return UserService(request.app.state.users)


def conflict_response(operation):
    try:
        return operation()
    except DuplicateEmail:
        raise HTTPException(409, "Ya existe un usuario con ese correo.") from None
    except UserNotFound:
        raise HTTPException(404, "El usuario no existe.") from None
    except InvalidReference:
        raise HTTPException(
            422, "Selecciona roles y una sucursal existentes."
        ) from None
    except AccessDenied:
        raise HTTPException(403, "No tienes permiso para asignar roles.") from None


@router.get("", response_model=UserListResponse)
def list_users(request: Request, actor: Actor):
    return {
        "users": service(request).list_users(actor),
        **request.app.state.users.options(),
        "current_user": actor,
    }


@router.post("", response_model=UserResponse, status_code=201)
def create_user(data: CreateUser, request: Request, actor: Actor):
    check_origin(request)
    return conflict_response(lambda: service(request).create(actor, data))


@router.patch("/{user_id}", response_model=UserResponse)
def update_user(user_id: UserId, data: UpdateUser, request: Request, actor: Actor):
    check_origin(request)
    return conflict_response(lambda: service(request).update(actor, user_id, data))


@router.post("/{user_id}/deactivate", response_model=UserResponse)
def deactivate_user(user_id: UserId, request: Request, actor: Actor):
    check_origin(request)
    return conflict_response(lambda: service(request).deactivate(actor, user_id))
