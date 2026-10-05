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
