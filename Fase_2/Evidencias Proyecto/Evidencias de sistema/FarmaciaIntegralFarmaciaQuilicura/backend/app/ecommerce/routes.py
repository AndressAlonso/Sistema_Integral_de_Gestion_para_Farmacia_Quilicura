from uuid import UUID

from fastapi import APIRouter, Query, Request, Response

from app.catalog.images import ProductImages
from app.ecommerce.schemas import BranchList, ProductList, PublicProduct
from app.ecommerce.service import PublicCatalogService

router = APIRouter(prefix="/api/ecommerce", tags=["ecommerce"])


def service(request: Request):
    return PublicCatalogService(request.app.state.ecommerce)


@router.get("/branches", response_model=BranchList)
def branches(request: Request):
    return service(request).branches()


@router.get("/products", response_model=ProductList)
def products(
    request: Request,
    q: str = Query(default="", max_length=150),
    branch_id: UUID | None = None,
):
    return service(request).products(q, branch_id)


@router.get("/products/{product_id}", response_model=PublicProduct)
def product(product_id: UUID, request: Request):
    return service(request).product(product_id)


@router.get("/products/{product_id}/image")
def image(product_id: UUID, request: Request):
    key = request.app.state.ecommerce.image_key(product_id)
    storage = getattr(request.app.state, "product_images", None) or ProductImages()
    return Response(storage.read(key), media_type="image/jpeg")
