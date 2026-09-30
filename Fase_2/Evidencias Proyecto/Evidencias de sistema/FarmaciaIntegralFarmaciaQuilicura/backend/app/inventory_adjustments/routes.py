from uuid import UUID

from fastapi import APIRouter, HTTPException, Request, Response
from sqlalchemy.exc import IntegrityError

from app.auth.routes import authenticated_user, check_origin
from app.inventory_adjustments.schemas import (
    AdjustmentResponse,
    CreateAdjustment,
    OperationOptions,
)
from app.inventory_adjustments.service import AdjustmentError, AdjustmentService

router = APIRouter(tags=["stock-operations"])


def execute(request, operation):
    actor, _ = authenticated_user(request)
    try:
        return operation(AdjustmentService(request.app.state.adjustments), actor)
    except AdjustmentError as exc:
        raise HTTPException(exc.status, exc.message) from None
    except IntegrityError:
        raise HTTPException(
            409,
            "Los datos cambiaron durante el ajuste. Actualiza y revisa las cantidades.",
        ) from None


@router.get("/api/stock-operations/options", response_model=OperationOptions)
def options(request: Request):
    return execute(request, lambda service, actor: service.options(actor))


@router.post(
    "/api/inventory-adjustments", status_code=201, response_model=AdjustmentResponse
)
def create(data: CreateAdjustment, request: Request, response: Response):
    check_origin(request)
    result, created = execute(
        request, lambda service, actor: service.create(actor, data)
    )
    response.status_code = 201 if created else 200
    return result


@router.get(
    "/api/inventory-adjustments/{adjustment_id}", response_model=AdjustmentResponse
)
def get(adjustment_id: UUID, request: Request):
    return execute(request, lambda service, actor: service.get(actor, adjustment_id))
