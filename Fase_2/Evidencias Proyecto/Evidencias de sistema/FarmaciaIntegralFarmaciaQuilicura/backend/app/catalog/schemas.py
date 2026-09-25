"""Contratos de categorias y productos del catalogo."""

from decimal import Decimal
from typing import Annotated
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator


Barcode = Annotated[
    str,
    Field(strict=True, min_length=1, max_length=128),
]


class CreateCategory(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
        str_strip_whitespace=True,
    )

    name: str = Field(strict=True, min_length=1, max_length=150)


class CategoryResponse(BaseModel):
    id: UUID
    name: str


class CreateProduct(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
        str_strip_whitespace=True,
    )

    sku: str = Field(strict=True, min_length=1, max_length=64)
    name: str = Field(strict=True, min_length=1, max_length=150)
    description: str = Field(default="", strict=True)
    category_id: UUID

    price: Decimal = Field(
        ge=0,
        lt=Decimal("1000000000000"),
        max_digits=14,
        decimal_places=2,
        allow_inf_nan=False,
    )

    requires_prescription: bool = Field(strict=True)
    is_active: bool = Field(default=True, strict=True)
    published_online: bool = Field(default=False, strict=True)
    barcodes: list[Barcode] = Field(default_factory=list)

    @field_validator("barcodes")
    @classmethod
    def validate_barcodes(cls, values: list[str]) -> list[str]:
        if len(values) != len(set(values)):
            raise ValueError("No repitas codigos de barras en el producto.")
        return values


class ProductResponse(BaseModel):
    id: UUID
    sku: str
    name: str
    description: str
    category_id: UUID
    price: Decimal
    requires_prescription: bool
    is_active: bool
    published_online: bool
    barcodes: list[str]