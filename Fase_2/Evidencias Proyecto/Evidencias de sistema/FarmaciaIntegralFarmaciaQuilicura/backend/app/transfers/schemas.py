from datetime import date, datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator

TransferState = Literal[
    "SOLICITADA", "AUTORIZADA", "EN_TRANSITO", "RECIBIDA", "RECHAZADA"
]


class TransferItem(BaseModel):
    model_config = ConfigDict(extra="forbid")
    product_id: UUID
    quantity: int = Field(strict=True, gt=0, le=1_000_000)


class CreateTransfer(BaseModel):
    model_config = ConfigDict(extra="forbid")
    request_id: UUID
    origin_id: UUID
    destination_id: UUID
    items: list[TransferItem] = Field(min_length=1, max_length=100)

    @model_validator(mode="after")
    def valid_request(self):
        if self.origin_id == self.destination_id:
            raise ValueError("Origen y destino deben ser distintos.")
        ids = [item.product_id for item in self.items]
        if len(ids) != len(set(ids)):
            raise ValueError("No repitas productos en la solicitud.")
        return self


class RejectTransfer(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    reason: str = Field(min_length=1, max_length=250)


class ReceiveTransfer(BaseModel):
    model_config = ConfigDict(extra="forbid")
    items: list[TransferItem] = Field(min_length=1, max_length=100)


class TransferLotResponse(BaseModel):
    number: str
    expiration_date: date
    quantity: int


class TransferItemResponse(TransferItem):
    product_name: str
    sku: str
    lots: list[TransferLotResponse]


class TransferEventResponse(BaseModel):
    event: str
    at: datetime
    user: str


class TransferResponse(BaseModel):
    order_id: UUID | None = None
    order_number: str | None = None
    id: UUID
    origin_id: UUID
    origin_name: str
    destination_id: UUID
    destination_name: str
    state: TransferState
    created_at: datetime
    requested_by: str
    rejection_reason: str | None
    actions: list[Literal["approve", "reject", "dispatch", "receive"]]
    items: list[TransferItemResponse]
    timeline: list[TransferEventResponse]


class TransferListResponse(BaseModel):
    transfers: list[TransferResponse]


class TransferBranchOption(BaseModel):
    id: UUID
    name: str


class TransferStockOption(BaseModel):
    product_id: UUID
    product_name: str
    sku: str
    branch_id: UUID
    available: int


class TransferOptionsResponse(BaseModel):
    branches: list[TransferBranchOption]
    stock: list[TransferStockOption]
    can_create: bool
    origin_ids: list[UUID]


class ReactivateDestinationLot(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    reason: str = Field(min_length=3, max_length=250)
    confirmed: Literal[True]
    expected_expiration_date: date
    expected_quantity: int = Field(strict=True, ge=0)


class ReceiptLotReview(BaseModel):
    product_name: str
    number: str
    incoming_quantity: int
    source_expiration: date
    destination_lot_id: UUID | None
    destination_expiration: date | None
    destination_active: bool | None
    destination_quantity: int | None
    conflicts: list[Literal["INACTIVE", "EXPIRATION_MISMATCH"]]
    can_reactivate: bool


class ReceiptReview(BaseModel):
    destination_name: str
    items: list[ReceiptLotReview]


class ReactivationResult(BaseModel):
    lot_id: UUID
    changed: bool
