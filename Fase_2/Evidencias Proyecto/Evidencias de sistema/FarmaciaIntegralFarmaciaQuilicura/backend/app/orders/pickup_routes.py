from typing import Literal
from uuid import UUID

from fastapi import APIRouter, Request
from pydantic import BaseModel, ConfigDict, Field, SecretStr

from app.auth.routes import authenticated_user, check_origin
from app.orders.pickup import PickupService

router = APIRouter(prefix="/api/orders/pickup", tags=["order-pickup"])


class PickupCode(BaseModel):
    model_config = ConfigDict(extra="forbid", hide_input_in_errors=True)
    code: SecretStr = Field(min_length=1, max_length=100)


class PickupConfirmation(PickupCode):
    expected_order_id: UUID
    confirmed: Literal[True]


@router.post("/validate")
def validate(data: PickupCode, request: Request):
    check_origin(request)
    actor = authenticated_user(request)[0]
    return PickupService(request.app.state.inventory.session_factory).process(actor, data.code.get_secret_value())


@router.post("/confirm")
def confirm(data: PickupConfirmation, request: Request):
    check_origin(request)
    actor = authenticated_user(request)[0]
    return PickupService(request.app.state.inventory.session_factory).process(actor, data.code.get_secret_value(), data.expected_order_id)
