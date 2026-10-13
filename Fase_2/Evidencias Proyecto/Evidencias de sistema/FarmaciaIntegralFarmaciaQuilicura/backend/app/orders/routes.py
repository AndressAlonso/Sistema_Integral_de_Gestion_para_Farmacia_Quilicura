from hashlib import sha256
from hmac import compare_digest
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, HTTPException, Query, Request, Response
from pydantic import BaseModel, ConfigDict, Field, SecretStr

from app.customers.routes import authenticated_customer, check_origin
from app.customers.security import COOKIE_NAME
from app.orders.models import PedidoOnline
from app.orders.schemas import CreateOrder
from app.orders.service import OrderService

router = APIRouter(tags=["orders"])


@router.post("/api/customers/orders")
def create_order(data: CreateOrder, request: Request, response: Response):
    check_origin(request)
    customer_id = (
        authenticated_customer(request)[0].id
        if request.cookies.get(COOKIE_NAME)
        else None
    )
    result, created = OrderService(request.app.state.inventory.session_factory).create(
        data, customer_id
    )
    response.status_code = 201 if created else 200
    return result


@router.get("/api/customers/orders")
def order_history(
    request: Request,
    limit: Annotated[int, Query(ge=1, le=100)] = 15,
    cursor: Annotated[str | None, Query(max_length=100)] = None,
):
    customer, _ = authenticated_customer(request)
    return OrderService(request.app.state.inventory.session_factory).history(
        customer.id, limit, cursor
    )


class OrderAccess(BaseModel):
    model_config = ConfigDict(extra="forbid", hide_input_in_errors=True)
    request_token: SecretStr = Field(min_length=64, max_length=64)


@router.post("/api/customers/orders/{order_id}/status")
def recover_order(order_id: UUID, data: OrderAccess, request: Request):
    check_origin(request)
    customer_id = (
        authenticated_customer(request)[0].id
        if request.cookies.get(COOKIE_NAME)
        else None
    )
    service = OrderService(request.app.state.inventory.session_factory)
    with service.factory.begin() as db:
        from sqlalchemy import text

        from app.orders.service import summary

        db.execute(
            text("SELECT pg_advisory_xact_lock(hashtextextended(:key, 0))"),
            {"key": "order:" + str(order_id)},
        )
        order = db.get(PedidoOnline, order_id)
        key_hash = sha256(data.request_token.get_secret_value().encode()).hexdigest()
        if (
            not order
            or order.cliente_id != customer_id
            or not compare_digest(order.clave_hash, key_hash)
        ):
            raise HTTPException(404, "No se encontró el pedido solicitado.")
        return summary(order)
