"""E2-H1: catalogo e imagenes con autorizacion en backend."""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from starlette.concurrency import run_in_threadpool

from app.auth.routes import authenticated_user, check_origin
from app.auth.users import User
from app.catalog.images import MAX_BYTES, ProductImages
from app.catalog.schemas import (
    CategoryResponse,
    CreateCategory,
    CreateProduct,
    ProductResponse,
    UpdateProduct,
)


def catalog_manager(request: Request) -> User:
    actor, _ = authenticated_user(request)
    if "catalogo.gestionar" not in actor.permissions:
        raise HTTPException(403, "No tienes permiso para gestionar el catalogo.")
    return actor


router = APIRouter(prefix="/api", tags=["catalog"])
Actor = Annotated[User, Depends(catalog_manager)]


def images(request: Request):
    return getattr(request.app.state, "product_images", None) or ProductImages()


@router.get("/categories", response_model=list[CategoryResponse])
def list_categories(request: Request, actor: Actor):
    return request.app.state.catalog.list_categories()


@router.post("/categories", response_model=CategoryResponse, status_code=201)
def create_category(data: CreateCategory, request: Request, actor: Actor):
    check_origin(request)
    return request.app.state.catalog.create_category(data.name)


@router.get("/products", response_model=list[ProductResponse])
def list_products(request: Request, actor: Actor):
    return request.app.state.catalog.list_products()


@router.post("/products", response_model=ProductResponse, status_code=201)
def create_product(data: CreateProduct, request: Request, actor: Actor):
    check_origin(request)
    return request.app.state.catalog.create_product(data)


@router.get("/products/{product_id}", response_model=ProductResponse)
def get_product(product_id: UUID, request: Request, actor: Actor):
    return request.app.state.catalog.get_product(product_id)


@router.patch("/products/{product_id}", response_model=ProductResponse)
def update_product(
    product_id: UUID, data: UpdateProduct, request: Request, actor: Actor
):
    check_origin(request)
    return request.app.state.catalog.update_product(product_id, data)


@router.post("/products/{product_id}/image", response_model=ProductResponse)
async def upload_image(product_id: UUID, request: Request, actor: Actor):
    check_origin(request)
    repository = request.app.state.catalog
    await run_in_threadpool(repository.get_product, product_id)
    data = bytearray()
    async for chunk in request.stream():
        if len(data) + len(chunk) > MAX_BYTES:
            raise HTTPException(413, "La imagen no puede superar los 5 MB.")
        data.extend(chunk)
    storage = images(request)

    def persist():
        key = storage.save(bytes(data))
        try:
            result, previous = repository.set_image(product_id, key)
        except Exception:
            storage.remove(key)
            raise
        storage.remove(previous)
        return result

    return await run_in_threadpool(persist)


@router.post("/products/{product_id}/image/remove", response_model=ProductResponse)
def remove_image(product_id: UUID, request: Request, actor: Actor):
    check_origin(request)
    result, previous = request.app.state.catalog.set_image(product_id, None)
    images(request).remove(previous)
    return result


@router.get("/products/{product_id}/image")
def get_image(product_id: UUID, request: Request, actor: Actor):
    key = request.app.state.catalog.image_key(product_id)
    return Response(
        images(request).read(key),
        media_type="image/jpeg",
        headers={"Cache-Control": "no-store", "X-Content-Type-Options": "nosniff"},
    )
