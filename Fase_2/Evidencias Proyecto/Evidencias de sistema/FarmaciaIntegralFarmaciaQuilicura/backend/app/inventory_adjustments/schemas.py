from datetime import date, datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator


class AdjustmentItem(BaseModel):
    model_config = ConfigDict(extra="forbid")
    lot_id: UUID
    expected_quantity: int = Field(strict=True, ge=0, le=2_147_483_647)
    new_quantity: int = Field(strict=True, ge=0, le=2_147_483_647)


class CreateAdjustment(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    request_id: UUID
    branch_id: UUID
    reason: str = Field(min_length=1, max_length=250)
    items: list[AdjustmentItem] = Field(min_length=1, max_length=100)

    @model_validator(mode="after")
    def unique_changes(self):
        ids = [item.lot_id for item in self.items]
        if len(ids) != len(set(ids)):
            raise ValueError("No repitas lotes en el ajuste.")
        if any(item.expected_quantity == item.new_quantity for item in self.items):
            raise ValueError("Incluye únicamente cantidades modificadas.")
        return self


class AdjustmentDetail(BaseModel):
    lot_id: UUID
    lot_number: str
    product_id: UUID
    product_name: str
    previous_quantity: int
    new_quantity: int
    difference: int


class AdjustmentResponse(BaseModel):
    id: UUID
    branch_id: UUID
    user_id: UUID
    reason: str
    created_at: datetime
    items: list[AdjustmentDetail]


class BranchOption(BaseModel):
    id: UUID
    name: str


class LotOption(BaseModel):
    id: UUID
    product_id: UUID
    product_name: str
    sku: str
    branch_id: UUID
    number: str
    expiration_date: date
    quantity: int


class ProductOption(BaseModel):
    id: UUID
    name: str
    sku: str
    branch_id: UUID
    quantity: int


class OperationOptions(BaseModel):
    products: list[ProductOption]
    branches: list[BranchOption]
    lots: list[LotOption]
    can_receive: bool
    can_adjust: bool
