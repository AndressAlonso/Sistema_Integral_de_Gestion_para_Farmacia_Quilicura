from decimal import Decimal
from typing import Literal
from uuid import UUID

from pydantic import Field, SecretStr

from app.ecommerce.cart.schemas import CartItemRequest, CartRequest
from app.ecommerce.guest.schemas import GuestData


class CreateOrder(CartRequest):
    request_id: UUID
    request_token: SecretStr = Field(min_length=64, max_length=64)
    pickup_branch_id: UUID
    items: list[CartItemRequest] = Field(min_length=1, max_length=50)
    guest: GuestData | None = None
    expected_total: Decimal = Field(ge=0, max_digits=18, decimal_places=2)
    confirmed: Literal[True]
