"""E2-H1: contratos públicos de categorías."""
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class CreateCategory(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    name: str = Field(strict=True, min_length=1, max_length=150)


class CategoryResponse(BaseModel):
    id: UUID
    name: str
