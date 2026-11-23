"""E7-H2: crea y reutiliza checkout; no confirma pagos ni modifica reservas."""

from datetime import datetime, timedelta, timezone
from hashlib import sha256
from hmac import compare_digest
from urllib.parse import urlsplit

from fastapi import HTTPException
from sqlalchemy import text

from app.orders.models import PedidoOnline
from app.payments.client import MercadoPagoClient, MercadoPagoError
from app.payments.models import CheckoutMercadoPago
from app.payments.preference import PreferenceValidationError, build_preference


def lock_order(db, order_id):
    db.execute(
        text("SELECT pg_advisory_xact_lock(hashtextextended(:key, 0))"),
        {"key": "order:" + str(order_id)},
    )


def authorize(order, customer_id, request_token):
    key_hash = sha256(request_token.encode()).hexdigest()
    if (
        order is None
        or order.cliente_id != customer_id
        or not compare_digest(order.clave_hash, key_hash)
    ):
        raise HTTPException(404, "No se encontró el pedido solicitado.")


def checkout_response(row):
    return {
        "order_id": str(row.pedido_id),
        "preference_id": row.preferencia_id,
        "checkout_url": row.checkout_url,
        "expires_at": row.vence_en.isoformat(),
    }


class PaymentService:
    def __init__(self, factory, settings, client=None):
        self.factory = factory
        self.settings = settings
        self.client = client or MercadoPagoClient(settings)

    def create_checkout(self, order_id, request_token, customer_id=None):
        if not self.settings.checkout_enabled or not self.settings.public_base_url:
            raise HTTPException(503, "El pago online todavía no está habilitado.")
        base = self.settings.public_base_url
        with self.factory.begin() as db:
            lock_order(db, order_id)
            order = db.get(PedidoOnline, order_id)
            authorize(order, customer_id, request_token)
            now = datetime.now(timezone.utc)
            if order.estado != "PENDIENTE_PAGO":
                raise HTTPException(409, "El pedido no está pendiente de pago.")
            if now >= order.creado_en + timedelta(minutes=15):
                raise HTTPException(409, "El plazo de pago del pedido terminó.")
            previous = db.get(CheckoutMercadoPago, order_id)
            if previous:
                if previous.estado == "LISTO":
                    return checkout_response(previous)
                raise HTTPException(
                    409,
                    "El intento de pago requiere confirmación. "
                    "No se creará otro enlace automáticamente.",
                )
            try:
                payload = build_preference(
                    order,
                    return_url=base + "/tienda/confirmar?order_id=" + str(order_id),
                    notification_url=base + "/api/payments/mercadopago/webhook",
                    now=now,
                )
            except PreferenceValidationError as error:
                raise HTTPException(409, str(error)) from None
            db.add(CheckoutMercadoPago(
                pedido_id=order_id, estado="CREANDO", total=order.total,
                moneda="CLP", creado_en=now, actualizado_en=now,
                vence_en=order.creado_en + timedelta(minutes=15),
            ))

        # El intento queda confirmado en BD antes de llamar al proveedor.
        # Un fallo o reinicio no autoriza una segunda creación automática.
        try:
            result = self.client.create_preference(payload)
            parsed = urlsplit(result["init_point"])
            if (
                parsed.scheme != "https"
                or parsed.hostname not in {"mercadopago.cl", "www.mercadopago.cl"}
                or parsed.username or parsed.password or parsed.fragment
                or len(result["id"]) > 200
            ):
                raise MercadoPagoError("El enlace recibido no es válido.")
        except (MercadoPagoError, ValueError, KeyError, TypeError):
            with self.factory.begin() as db:
                lock_order(db, order_id)
                row = db.get(CheckoutMercadoPago, order_id)
                row.estado = "INCIERTO"
                row.actualizado_en = datetime.now(timezone.utc)
            raise HTTPException(
                502,
                "No pudimos confirmar el enlace de pago. "
                "El intento quedó registrado para revisión.",
            ) from None

        with self.factory.begin() as db:
            lock_order(db, order_id)
            row = db.get(CheckoutMercadoPago, order_id)
            row.estado = "LISTO"
            row.preferencia_id = result["id"]
            row.checkout_url = result["init_point"]
            row.actualizado_en = datetime.now(timezone.utc)
            response = checkout_response(row)
            order = db.get(PedidoOnline, order_id)
            can_pay = (
                order.estado == "PENDIENTE_PAGO"
                and row.actualizado_en < row.vence_en
            )
        if not can_pay:
            raise HTTPException(409, "El pedido ya no está disponible para pagar.")
        return response
