from datetime import datetime
from decimal import Decimal
from typing import Literal
from uuid import UUID

from pydantic import (
    AwareDatetime,
    BaseModel,
    ConfigDict,
    Field,
    field_validator,
    model_validator,
)


class PromotionInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    name: str = Field(min_length=1, max_length=150)
    kind: Literal["PERCENT", "FIXED_PRICE"]
    value: Decimal = Field(ge=0, lt=1000000000000, max_digits=14, decimal_places=2)
    starts_at: AwareDatetime
    ends_at: AwareDatetime
    product_id: UUID | None = None
    category_id: UUID | None = None
    is_active: bool = True

    @field_validator("name")
    @classmethod
    def clean_name(cls, value):
        value = value.strip()
        if not value:
            raise ValueError("Ingresa un nombre.")
        return value

    @model_validator(mode="after")
    def valid_promotion(self):
        if self.ends_at <= self.starts_at:
            raise ValueError("El término debe ser posterior al inicio.")
        if (self.product_id is None) == (self.category_id is None):
            raise ValueError("Selecciona un producto o una categoría, exclusivamente.")
        if self.kind == "PERCENT" and self.value > 100:
            raise ValueError("El porcentaje no puede superar 100.")
        return self


class PromotionResponse(PromotionInput):
    id: UUID
    created_at: datetime
