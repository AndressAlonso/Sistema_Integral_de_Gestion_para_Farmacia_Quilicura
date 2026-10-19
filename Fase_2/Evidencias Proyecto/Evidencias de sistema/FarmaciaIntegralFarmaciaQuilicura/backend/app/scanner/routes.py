"""E8-H1: rutas autenticadas de vinculación del escáner."""

from uuid import UUID

from fastapi import APIRouter, HTTPException, Request

from app.auth.routes import COOKIE_NAME, authenticated_user, check_origin
from app.scanner.schemas import (
    ClaimScanner,
    CreateScannerLinkResponse,
    ScannerLinkResponse,
    ScannerReadResponse,
    SubmitScannerRead,
)
from app.scanner.service import ScannerError

router = APIRouter(
    prefix="/api/scanner",
    tags=["Escáner móvil — E8"],
)


def execute(request: Request, operation):
    actor, _ = authenticated_user(request)

    if request.method != "GET":
        check_origin(request)

    token = request.cookies.get(COOKIE_NAME, "")

    try:
        return operation(request.app.state.scanner, actor, token)
    except ScannerError as exc:
        raise HTTPException(exc.status, exc.message) from None


@router.post(
    "/links",
    response_model=CreateScannerLinkResponse,
    status_code=201,
)
def create_link(request: Request):
    return execute(
        request,
        lambda service, actor, token: service.create(actor, token),
    )


@router.post(
    "/links/claim",
    response_model=ScannerLinkResponse,
)
def claim_link(data: ClaimScanner, request: Request):
    return execute(
        request,
        lambda service, actor, token: service.claim(
            actor,
            token,
            data.pairing_code,
        ),
    )


@router.get(
    "/links/{link_id}",
    response_model=ScannerLinkResponse,
)
def link_status(link_id: UUID, request: Request):
    return execute(
        request,
        lambda service, actor, token: service.status(
            actor,
            token,
            link_id,
        ),
    )


@router.post(
    "/links/{link_id}/revoke",
    response_model=ScannerLinkResponse,
)
def revoke_link(link_id: UUID, request: Request):
    return execute(
        request,
        lambda service, actor, token: service.revoke(
            actor,
            token,
            link_id,
        ),
    )

@router.post(
    "/links/{link_id}/reads",
    response_model=ScannerReadResponse,
)
def submit_read(
    link_id: UUID,
    data: SubmitScannerRead,
    request: Request,
):
    return execute(
        request,
        lambda service, actor, token: service.submit_read(
            actor,
            token,
            link_id,
            data.request_id,
            data.code,
        ),
    )


@router.get(
    "/links/{link_id}/reads",
    response_model=list[ScannerReadResponse],
)
def pending_reads(link_id: UUID, request: Request):
    return execute(
        request,
        lambda service, actor, token: service.pending_reads(
            actor,
            token,
            link_id,
        ),
    )


@router.post(
    "/links/{link_id}/reads/{read_id}/ack",
    response_model=ScannerReadResponse,
)
def acknowledge_read(
    link_id: UUID,
    read_id: UUID,
    request: Request,
):
    return execute(
        request,
        lambda service, actor, token: service.acknowledge_read(
            actor,
            token,
            link_id,
            read_id,
        ),
    )