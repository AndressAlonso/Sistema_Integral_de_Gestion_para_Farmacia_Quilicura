from uuid import UUID

from fastapi import APIRouter, HTTPException, Request, Response
from sqlalchemy.exc import IntegrityError

from app.auth.routes import authenticated_user, check_origin
from app.transfers.schemas import (
    CreateTransfer,
    ReceiveTransfer,
    RejectTransfer,
    TransferListResponse,
    TransferOptionsResponse,
    TransferResponse,
)
from app.transfers.service import TransferError, TransferService

router = APIRouter(prefix="/api/transfers", tags=["transfers"])


def execute(request, operation):
    actor, _ = authenticated_user(request)
    try:
        return operation(TransferService(request.app.state.transfers), actor)
    except TransferError as exc:
        raise HTTPException(exc.status, exc.message) from None
    except IntegrityError:
        raise HTTPException(
            409,
            "Los datos cambiaron durante la operación. Actualiza y revisa la transferencia.",
        ) from None


@router.get("", response_model=TransferListResponse)
def list_transfers(request: Request):
    return execute(request, lambda service, actor: service.list(actor))


@router.get("/options", response_model=TransferOptionsResponse)
def options(request: Request):
    return execute(request, lambda service, actor: service.options(actor))


@router.get("/{transfer_id}", response_model=TransferResponse)
def get_transfer(transfer_id: UUID, request: Request):
    return execute(request, lambda service, actor: service.get(actor, transfer_id))


@router.post("", status_code=201, response_model=TransferResponse)
def create_transfer(data: CreateTransfer, request: Request, response: Response):
    check_origin(request)
    result, created = execute(
        request, lambda service, actor: service.create(actor, data)
    )
    response.status_code = 201 if created else 200
    return result


@router.post("/{transfer_id}/approve", response_model=TransferResponse)
def approve(transfer_id: UUID, request: Request):
    check_origin(request)
    return execute(
        request, lambda service, actor: service.change(actor, transfer_id, "approve")
    )


@router.post("/{transfer_id}/reject", response_model=TransferResponse)
def reject(transfer_id: UUID, data: RejectTransfer, request: Request):
    check_origin(request)
    return execute(
        request,
        lambda service, actor: service.change(actor, transfer_id, "reject", data),
    )


@router.post("/{transfer_id}/dispatch", response_model=TransferResponse)
def dispatch(transfer_id: UUID, request: Request):
    check_origin(request)
    return execute(
        request, lambda service, actor: service.change(actor, transfer_id, "dispatch")
    )


@router.post("/{transfer_id}/receive", response_model=TransferResponse)
def receive(transfer_id: UUID, data: ReceiveTransfer, request: Request):
    check_origin(request)
    return execute(
        request,
        lambda service, actor: service.change(actor, transfer_id, "receive", data),
    )
