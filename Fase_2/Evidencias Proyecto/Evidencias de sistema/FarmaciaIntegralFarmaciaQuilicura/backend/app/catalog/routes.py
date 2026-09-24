"""E2-H1: lectura y creación de categorías con autorización en backend."""
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request

from app.auth.routes import authenticated_user, check_origin
from app.auth.users import User
from app.catalog.schemas import CategoryResponse, CreateCategory


def catalog_manager(request: Request) -> User:
    actor, _ = authenticated_user(request)
    if "catalogo.gestionar" not in actor.permissions:
        raise HTTPException(403, "No tienes permiso para gestionar el catálogo.")
    return actor


router = APIRouter(prefix="/api/categories", tags=["catalog"])
Actor = Annotated[User, Depends(catalog_manager)]


@router.get("", response_model=list[CategoryResponse])
def list_categories(request: Request, actor: Actor):
    return request.app.state.catalog.list_categories()


@router.post("", response_model=CategoryResponse, status_code=201)
def create_category(data: CreateCategory, request: Request, actor: Actor):
    check_origin(request)
    return request.app.state.catalog.create_category(data.name)
