from datetime import date, datetime
from uuid import UUID

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    field_validator,
)


class InventoryRecordResponse(BaseModel):
    model_config = ConfigDict(
        from_attributes=True,
        extra="forbid",
    )

    id: UUID

    product_id: UUID
    product_name: str
    product_sku: str

    branch_id: UUID
    branch_name: str
    branch_code: str

    physical: int = Field(ge=0)
    reserved: int = Field(ge=0)
    available: int = Field(ge=0)


class InventoryListResponse(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
    )

    records: list[InventoryRecordResponse]


class CreateInventoryLot(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
        str_strip_whitespace=True,
    )

    inventory_id: UUID

    lot_number: str = Field(
        min_length=1,
        max_length=80,
    )

    expiration_date: date

    quantity: int = Field(
        gt=0,
    )

    @field_validator("expiration_date")
    @classmethod
    def validate_expiration_date(
        cls,
        value: date,
    ) -> date:
        if value <= date.today():
            raise ValueError(
                "La fecha de vencimiento debe ser futura."
            )

        return value


class InventoryLotResponse(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
    )

    id: UUID
    inventory_id: UUID

    product_id: UUID
    product_name: str
    product_sku: str

    branch_id: UUID
    branch_name: str
    branch_code: str

    lot_number: str
    expiration_date: date
    quantity: int = Field(ge=0)
    is_active: bool
    created_at: datetime


class InventoryLotListResponse(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
    )

    lots: list[InventoryLotResponse]
