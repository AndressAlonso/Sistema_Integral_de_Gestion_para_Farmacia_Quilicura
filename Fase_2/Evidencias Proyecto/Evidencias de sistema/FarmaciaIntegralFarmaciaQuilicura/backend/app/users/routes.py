from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request, Response

from app.auth.routes import authenticated_user, check_origin
from app.auth.users import (
    DuplicateEmail,
    InvalidDeletionConfirmation,
    InvalidReference,
    User,
    UserDeletionBlocked,
    UserNotFound,
)
from app.users.schemas import (
    CreateUser,
    DeleteUser,
    UpdateUser,
    UserListResponse,
    UserResponse,
)
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
    except InvalidDeletionConfirmation:
        raise HTTPException(422, "El correo de confirmación no coincide.") from None
    except UserDeletionBlocked as exc:
        raise HTTPException(409, str(exc)) from None
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
    users = service(request).list_users(actor)
    options = request.app.state.users.deletion_options(actor.id)
    return {
        "users": [
            UserResponse.model_validate(user).model_copy(update={
                "can_delete": user.id in options and options[user.id] is None,
                "deletion_block_reason": options.get(user.id),
            }) for user in users
        ],
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


@router.post("/{user_id}/delete", status_code=204, response_class=Response)
def delete_user(user_id: UserId, data: DeleteUser, request: Request, actor: Actor):
    check_origin(request)
    conflict_response(lambda: service(request).delete(actor, user_id, str(data.confirmation_email)))
    return Response(status_code=204)


@router.post("/{user_id}/activate", response_model=UserResponse)
def activate_user(user_id: UserId, request: Request, actor: Actor):
    check_origin(request)
    return conflict_response(lambda: service(request).activate(actor, user_id))
