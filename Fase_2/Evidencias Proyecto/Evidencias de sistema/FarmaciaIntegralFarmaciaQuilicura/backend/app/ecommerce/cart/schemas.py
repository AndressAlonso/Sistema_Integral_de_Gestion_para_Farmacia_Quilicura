from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.ecommerce.schemas import PublicBranch


class CartItemRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    product_id: UUID
    quantity: int = Field(strict=True, ge=1, le=99)


class CartRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    items: list[CartItemRequest] = Field(max_length=50)
    pickup_branch_id: UUID | None = None

    @model_validator(mode="after")
    def distinct_products(self):
        if len({item.product_id for item in self.items}) != len(self.items):
            raise ValueError("Productos duplicados")
        return self


class CartLine(BaseModel):
    product_id: UUID
    name: str | None = None
    quantity: int
    unit_price: Decimal | None = None
    subtotal: Decimal | None = None
    local_available: int | None = None
    global_available: int = 0
    requires_transfer: bool = False
    valid: bool = False
    issues: list[str] = Field(default_factory=list)


class CartResponse(BaseModel):
    valid: bool
    pickup_branch: PublicBranch | None
    items: list[CartLine]
    total: Decimal | None
    currency: str = "CLP"
    issues: list[str]
