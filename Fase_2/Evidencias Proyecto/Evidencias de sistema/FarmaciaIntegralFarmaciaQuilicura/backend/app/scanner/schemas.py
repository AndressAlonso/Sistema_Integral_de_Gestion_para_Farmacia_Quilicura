"""E8-H1: contratos de vinculación entre POS y aplicación móvil."""

from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


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