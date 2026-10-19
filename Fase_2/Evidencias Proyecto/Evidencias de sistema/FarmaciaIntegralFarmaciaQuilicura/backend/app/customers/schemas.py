from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, Field, SecretStr, field_validator


def normalize_email(value: str) -> str:
    return value.strip().lower()


class LoginRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", hide_input_in_errors=True)
    email: EmailStr = Field(max_length=254)
    password: SecretStr = Field(min_length=12, max_length=128)

    @field_validator("email", mode="before")
    @classmethod
    def trim_email(cls, value):
        return value.strip() if isinstance(value, str) else value

    @field_validator("email")
    @classmethod
    def normalized_email(cls, value):
        return normalize_email(str(value))


class RegisterRequest(LoginRequest):
    name: str = Field(min_length=1, max_length=150)

    @field_validator("name", mode="before")
    @classmethod
    def trim_name(cls, value):
        return value.strip() if isinstance(value, str) else value


class PublicCustomer(BaseModel):
    id: UUID
    name: str
    email: EmailStr


class SessionResponse(BaseModel):
    customer: PublicCustomer
    expires_at: datetime
