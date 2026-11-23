"""E7-H2: acceso al checkout con sesión de cliente y/o clave del pedido."""

from uuid import UUID

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, ConfigDict, Field, SecretStr, ValidationError

from app.customers.routes import authenticated_customer, check_origin
from app.customers.security import COOKIE_NAME
from app.payments.config import PaymentSettings
from app.payments.processor import PaymentNotificationService
from app.payments.service import PaymentService
from app.payments.signature import (
    InvalidWebhookSignature,
    WebhookNotConfigured,
    verified_payment_id,
)

router = APIRouter(prefix="/api/customers/orders", tags=["payments"])


class CheckoutAccess(BaseModel):
    model_config = ConfigDict(extra="forbid", hide_input_in_errors=True)
    request_token: SecretStr = Field(min_length=64, max_length=64)


@router.post("/{order_id}/checkout")
def create_checkout(order_id: UUID, data: CheckoutAccess, request: Request):
    check_origin(request)
    customer_id = (
        authenticated_customer(request)[0].id
        if request.cookies.get(COOKIE_NAME)
        else None
    )
    try:
        settings = PaymentSettings()
    except ValidationError:
        raise HTTPException(
            503, "La configuración del pago no está disponible."
        ) from None
    return PaymentService(
        request.app.state.inventory.session_factory,
        settings,
    ).create_checkout(order_id, data.request_token.get_secret_value(), customer_id)


webhook_router = APIRouter(prefix="/api/payments/mercadopago", tags=["payments"])


@webhook_router.post("/webhook")
def payment_webhook(request: Request):
    try:
        settings = PaymentSettings()
        payment_id = verified_payment_id(request, settings.webhook_secret)
    except (ValidationError, WebhookNotConfigured):
        raise HTTPException(
            503, "La configuración del webhook no está disponible."
        ) from None
    except InvalidWebhookSignature:
        raise HTTPException(401, "Notificación no autenticada.") from None
    return PaymentNotificationService(
        request.app.state.inventory.session_factory,
        settings,
    ).process(payment_id)
