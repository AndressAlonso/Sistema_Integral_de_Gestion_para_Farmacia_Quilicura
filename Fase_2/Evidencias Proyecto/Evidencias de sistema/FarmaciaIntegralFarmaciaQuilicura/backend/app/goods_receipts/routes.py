from uuid import UUID

from fastapi import APIRouter, HTTPException, Request, Response
from sqlalchemy.exc import IntegrityError

from app.auth.routes import authenticated_user, check_origin
from app.goods_receipts.schemas import CreateReceipt, ReceiptResponse
from app.goods_receipts.service import ReceiptError, ReceiptService

router = APIRouter(prefix="/api/goods-receipts", tags=["goods-receipts"])


def execute(request, operation):
    actor, _ = authenticated_user(request)
    service = ReceiptService(request.app.state.goods_receipts)
    try:
        return operation(service, actor)
    except ReceiptError as exc:
        raise HTTPException(exc.status, exc.message) from None
    except IntegrityError:
        raise HTTPException(409, "Los datos cambiaron durante el registro. Revisa la entrada.") from None


@router.get("/options")
def options(request: Request):
    return execute(request, lambda service, actor: service.options(actor))


@router.get("/{receipt_id}", response_model=ReceiptResponse)
def get_receipt(receipt_id: UUID, request: Request):
    return execute(request, lambda service, actor: service.get(actor, receipt_id))


@router.post("", response_model=ReceiptResponse, status_code=201)
def create_receipt(data: CreateReceipt, request: Request, response: Response):
    check_origin(request)
    result, created = execute(request, lambda service, actor: service.create(actor, data))
    response.status_code = 201 if created else 200
    return result
