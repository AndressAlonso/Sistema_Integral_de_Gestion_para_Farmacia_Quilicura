"""E7-H4: contratos internos; no modifica los endpoints del cliente."""
from typing import Annotated, Literal
from uuid import UUID

from fastapi import APIRouter, Query, Request
from pydantic import BaseModel, ConfigDict, Field

from app.auth.routes import authenticated_user, check_origin
from app.orders.preparation import PreparationService

router = APIRouter(prefix="/api/orders", tags=["order-preparation"])


def context(request):
    return PreparationService(request.app.state.inventory.session_factory), authenticated_user(request)[0]


class Transition(BaseModel):
    model_config = ConfigDict(extra="forbid")
    expected_state: str = Field(max_length=30)


@router.get("")
def list_orders(request: Request, state: str | None = None, branch_id: UUID | None = None,
                page: int = Query(default=1, ge=1), limit: int = Query(default=15, ge=1, le=100),
                states: Annotated[list[str] | None, Query(max_length=5)] = None,
                sort: Literal["newest", "state_asc", "state_desc", "branch_asc", "branch_desc"] = "newest",
                branch_ids: Annotated[list[UUID] | None, Query(max_length=100)] = None):
    service, actor = context(request)
    return service.list(actor, state, branch_id, page, limit, states, sort, branch_ids)


@router.get("/{order_id}")
def detail(order_id: UUID, request: Request):
    service, actor = context(request)
    return service.get(actor, order_id)


@router.post("/{order_id}/preparation")
def prepare(order_id: UUID, data: Transition, request: Request):
    check_origin(request)
    service, actor = context(request)
    return service.change(actor, order_id, "preparation", data.expected_state)


@router.post("/{order_id}/ready")
def ready(order_id: UUID, data: Transition, request: Request):
    check_origin(request)
    service, actor = context(request)
    return service.change(actor, order_id, "ready", data.expected_state)
