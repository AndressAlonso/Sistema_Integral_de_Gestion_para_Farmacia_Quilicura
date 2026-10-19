"""E8-H1: contratos de vinculación entre POS y aplicación móvil."""

from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator


class ClaimScanner(BaseModel):
    model_config = ConfigDict(extra="forbid")

    pairing_code: str = Field(
        strict=True,
        min_length=43,
        max_length=43,
        pattern=r"^[A-Za-z0-9_-]{43}$",
    )


class ScannerLinkResponse(BaseModel):
    id: UUID
    state: Literal[
        "PENDING",
        "LINKED",
        "REVOKED",
        "EXPIRED",
        "DISCONNECTED",
    ]
    cash_id: UUID
    branch_id: UUID
    qr_expires_at: datetime
    expires_at: datetime
    linked_at: datetime | None


class CreateScannerLinkResponse(ScannerLinkResponse):
    pairing_code: str

class SubmitScannerRead(BaseModel):
    model_config = ConfigDict(extra="forbid")

    request_id: UUID
    code: str = Field(strict=True, min_length=1, max_length=128)

    @field_validator("code")
    @classmethod
    def validate_code(cls, value: str) -> str:
        if value != value.strip():
            raise ValueError("El código no puede tener espacios en los extremos.")

        if any(ord(character) < 32 or ord(character) == 127 for character in value):
            raise ValueError("El código contiene caracteres de control.")

        return value


class ScannerReadResponse(BaseModel):
    id: UUID
    sequence: int
    link_id: UUID
    code: str
    product_id: UUID | None
    result: Literal["FOUND", "NOT_FOUND", "INACTIVE"]
    created_at: datetime
    received_at: datetime | None