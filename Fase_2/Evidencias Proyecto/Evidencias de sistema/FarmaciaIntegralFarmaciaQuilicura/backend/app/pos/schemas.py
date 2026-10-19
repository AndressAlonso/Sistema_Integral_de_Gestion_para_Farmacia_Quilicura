from decimal import Decimal
from typing import Annotated, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator

Amount = Annotated[
    Decimal, Field(ge=0, lt=1000000000000, max_digits=14, decimal_places=2)
]


class Input(BaseModel):
    model_config = ConfigDict(extra="forbid")


class CartItem(Input):
    product_id: UUID
    quantity: Annotated[int, Field(strict=True, ge=1, le=1000000)]


class Cart(Input):
    items: list[CartItem] = Field(min_length=1, max_length=100)

    @model_validator(mode="after")
    def unique_products(self):
        if len({item.product_id for item in self.items}) != len(self.items):
            raise ValueError("Cada producto debe aparecer una sola vez")
        return self


class SaleInput(Cart):
    request_id: UUID
    payment: Literal["EFECTIVO", "DEBITO", "CREDITO", "TRANSFERENCIA"]
    quote_version: str = Field(min_length=64, max_length=64)


class OpenCash(Input):
    request_id: UUID
    initial_amount: Amount


class CloseCash(Input):
    counted_cash: Amount
    summary_version: str = Field(min_length=64, max_length=64)


class ReturnItem(CartItem):
    sale_lot_id: UUID
    restock: bool = Field(strict=True)
    condition: str = Field(min_length=1, max_length=250, pattern=r"\S")


class ReversalInput(Input):
    request_id: UUID
    kind: Literal["ANULACION", "DEVOLUCION"]
    reason: str = Field(min_length=1, max_length=250, pattern=r"\S")
    items: list[ReturnItem] = Field(min_length=1, max_length=100)

    @model_validator(mode="after")
    def unique_products(self):
        if len({item.sale_lot_id for item in self.items}) != len(self.items):
            raise ValueError("No repitas lotes vendidos")
        return self
