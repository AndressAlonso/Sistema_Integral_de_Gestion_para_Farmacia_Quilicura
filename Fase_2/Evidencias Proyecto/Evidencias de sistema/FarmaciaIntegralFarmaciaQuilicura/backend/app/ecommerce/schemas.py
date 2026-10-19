from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, Field

from app.promotions.pricing import AppliedPromotion


class PublicBranch(BaseModel):
    id: UUID
    name: str
    address: str


class BranchList(BaseModel):
    branches: list[PublicBranch]


class PublicCategory(BaseModel):
    id: UUID
    name: str


class Availability(BaseModel):
    branch_id: UUID
    branch_name: str
    available: int = Field(ge=0)


class PublicProduct(BaseModel):
    id: UUID
    name: str
    description: str
    category: PublicCategory
    price: Decimal
    base_price: Decimal | None = None
    discount: Decimal = Field(default=Decimal(0), ge=0)
    promotion: AppliedPromotion | None = None
    requires_prescription: bool
    # Restricción del canal, no confirmación de unidades vendibles.
    online_purchase_allowed: bool
    image_url: str | None
    availability: list[Availability]


class ProductList(BaseModel):
    products: list[PublicProduct]
