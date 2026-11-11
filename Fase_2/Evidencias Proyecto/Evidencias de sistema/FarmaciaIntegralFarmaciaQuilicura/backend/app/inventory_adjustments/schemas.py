from datetime import date, datetime
from uuid import UUID
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

ReasonType = Literal["CONTEO", "DANADO", "VENCIMIENTO", "OTRO"]
REASON_LABELS = {"CONTEO": "Diferencia de conteo", "DANADO": "Producto dañado", "VENCIMIENTO": "Vencimiento", "OTRO": "Otro"}


class AdjustmentItem(BaseModel):
    model_config = ConfigDict(extra="forbid")
    lot_id: UUID
    expected_quantity: int = Field(strict=True, ge=0, le=2_147_483_647)
    new_quantity: int = Field(strict=True, ge=0, le=2_147_483_647)
    expected_reserved: int | None = Field(default=None, strict=True, ge=0)


class CreateAdjustment(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    request_id: UUID
    branch_id: UUID
    reason: str = Field(default="", max_length=250)
    reason_type: ReasonType | None = None
    items: list[AdjustmentItem] = Field(min_length=1, max_length=100)

    @model_validator(mode="after")
    def unique_changes(self):
        if (self.reason_type is None or self.reason_type == "OTRO") and not self.reason:
            raise ValueError("Explica el motivo del ajuste.")
        if self.reason_type and len(self.reason) > 220:
            raise ValueError("La observación admite hasta 220 caracteres.")
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
    reason_type: ReasonType | None = None
    created_at: datetime
    items: list[AdjustmentDetail]


class BranchOption(BaseModel):
    id: UUID
    name: str


class LotOption(BaseModel):
    available: int
    is_active: bool
    product_active: bool
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
