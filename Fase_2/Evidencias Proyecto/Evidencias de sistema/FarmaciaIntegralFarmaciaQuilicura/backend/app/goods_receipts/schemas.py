"""E4-H4: contrato de entrada documental; cantidades expresadas en unidades de stock."""

from datetime import date, datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator


class ReceiptItem(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    product_id: UUID
    lot_number: str = Field(min_length=1, max_length=80)
    expiration_date: date
    quantity: int = Field(strict=True, gt=0, le=1_000_000)


class CreateReceipt(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    request_id: UUID
    branch_id: UUID
    supplier: str = Field(min_length=1, max_length=150)
    document_type: Literal["GUIA", "FACTURA"]
    document_number: str = Field(min_length=1, max_length=80)
    document_date: date
    items: list[ReceiptItem] = Field(min_length=1, max_length=100)

    @model_validator(mode="after")
    def unique_items(self):
        keys = [(item.product_id, item.lot_number) for item in self.items]
        if len(keys) != len(set(keys)):
            raise ValueError("No repitas el mismo producto y lote en la entrada.")
        return self


class ReceiptResponse(BaseModel):
    id: UUID
    branch_id: UUID
    user_id: UUID
    supplier: str
    document_type: str
    document_number: str
    document_date: date
    created_at: datetime
    items: list[ReceiptItem]
