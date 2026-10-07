from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator

from app.ecommerce.cart.schemas import CartRequest, CartResponse


class GuestData(BaseModel):
    model_config = ConfigDict(extra="forbid", hide_input_in_errors=True)
    name: str = Field(min_length=1, max_length=150, repr=False)
    email: EmailStr = Field(max_length=254, repr=False)

    @field_validator("name", "email", mode="before")
    @classmethod
    def trim(cls, value):
        return value.strip() if isinstance(value, str) else value

    @field_validator("email")
    @classmethod
    def normalize_email(cls, value):
        return str(value).lower()


class GuestCartRequest(CartRequest):
    pickup_branch_id: UUID


class GuestValidationRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", hide_input_in_errors=True)
    guest: GuestData = Field(repr=False)
    cart: GuestCartRequest


class GuestValidationResponse(BaseModel):
    model_config = ConfigDict(extra="forbid", hide_input_in_errors=True)
    guest: GuestData = Field(repr=False)
    cart: CartResponse
