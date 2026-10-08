from uuid import UUID

from fastapi import APIRouter, HTTPException, Query, Request, Response
from sqlalchemy.exc import IntegrityError

from app.auth.routes import authenticated_user, check_origin
from app.catalog.images import ProductImages
from app.pos.pricing import development_promotions
from app.pos.schemas import Cart, CloseCash, OpenCash, ReversalInput, SaleInput
from app.pos.service import PosError, PosService

router = APIRouter(prefix="/api", tags=["POS y caja — E5"])


def execute(request, operation):
    actor, _ = authenticated_user(request)
    if request.method != "GET":
        check_origin(request)
    try:
        return operation(
            PosService(
                request.app.state.pos,
                development_promotions(request.app.state.settings),
            ),
            actor,
        )
    except PosError as exc:
        raise HTTPException(exc.status, exc.message) from None
    except IntegrityError:
        raise HTTPException(
            409,
            "La operación entra en conflicto con los datos actuales. Actualiza y revisa.",
        ) from None


@router.get("/pos/products")
def products(request: Request, q: str = Query(default="", max_length=128)):
    return execute(request, lambda service, actor: service.products(actor, q.strip()))


@router.post("/pos/quote")
def quote(data: Cart, request: Request):
    return execute(request, lambda service, actor: service.quote(actor, data))


@router.get("/pos/products/{product_id}/image")
def product_image(product_id: UUID, request: Request):
    key = execute(request, lambda service, actor: service.product_image_key(actor, product_id))
    storage = getattr(request.app.state, "product_images", None) or ProductImages()
    return Response(
        storage.read(key),
        media_type="image/jpeg",
        headers={"Cache-Control": "no-store", "X-Content-Type-Options": "nosniff"},
    )


@router.post("/pos/sales")
def sell(data: SaleInput, request: Request):
    return execute(request, lambda service, actor: service.sell(actor, data))


@router.get("/pos/sales")
def list_sales(request: Request):
    return execute(request, lambda service, actor: service.list_sales(actor))


@router.post("/pos/sales/{sale_id}/reversals")
def reverse(sale_id: UUID, data: ReversalInput, request: Request):
    return execute(
        request, lambda service, actor: service.reverse(actor, sale_id, data)
    )


@router.get("/pos/sales/{sale_id}/receipt")
def receipt(sale_id: UUID, request: Request):
    return execute(request, lambda service, actor: service.receipt(actor, sale_id))


@router.get("/cash/current")
def current(request: Request):
    return execute(request, lambda service, actor: service.current(actor))


@router.post("/cash/open")
def open_cash(data: OpenCash, request: Request):
    return execute(request, lambda service, actor: service.open(actor, data))


@router.get("/cash/{cash_id}/summary")
def summary(cash_id: UUID, request: Request):
    return execute(request, lambda service, actor: service.summary(actor, cash_id))


@router.post("/cash/{cash_id}/close")
def close(cash_id: UUID, data: CloseCash, request: Request):
    return execute(request, lambda service, actor: service.close(actor, cash_id, data))
