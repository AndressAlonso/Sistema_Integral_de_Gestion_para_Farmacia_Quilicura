from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


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