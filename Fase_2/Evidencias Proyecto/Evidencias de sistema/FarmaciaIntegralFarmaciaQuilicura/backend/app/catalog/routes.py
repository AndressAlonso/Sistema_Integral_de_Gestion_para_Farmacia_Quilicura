"""API de categorias y productos con autorizacion."""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request

from app.auth.routes import authenticated_user, check_origin
from app.auth.users import User
from app.catalog.schemas import (
    CategoryResponse,
    CreateCategory,
    CreateProduct,
    ProductResponse,
)


def catalog_manager(request: Request) -> User:
    actor, _ = authenticated_user(request)

    if "catalogo.gestionar" not in actor.permissions:
        raise HTTPException(
            status_code=403,
            detail="No tienes permiso para gestionar el catalogo.",
        )

    return actor


router = APIRouter(prefix="/api", tags=["catalog"])
Actor = Annotated[User, Depends(catalog_manager)]


@router.get("/categories", response_model=list[CategoryResponse])
def list_categories(request: Request, actor: Actor):
    return request.app.state.catalog.list_categories()


@router.post(
    "/categories",
    response_model=CategoryResponse,
    status_code=201,
)
def create_category(
    data: CreateCategory,
    request: Request,
    actor: Actor,
):
    check_origin(request)
    return request.app.state.catalog.create_category(data.name)


@router.get("/products", response_model=list[ProductResponse])
def list_products(request: Request, actor: Actor):
    return request.app.state.catalog.list_products()


@router.post(
    "/products",
    response_model=ProductResponse,
    status_code=201,
)
def create_product(
    data: CreateProduct,
    request: Request,
    actor: Actor,
):
    check_origin(request)
    return request.app.state.catalog.create_product(data)