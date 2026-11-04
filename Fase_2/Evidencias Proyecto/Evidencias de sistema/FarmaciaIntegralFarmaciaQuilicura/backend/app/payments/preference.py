"""E7-H2: construye la preferencia desde un pedido persistido."""

from datetime import datetime, timedelta, timezone
from decimal import Decimal
from urllib.parse import urlsplit


class PreferenceValidationError(ValueError):
    pass


def public_https_url(value: str) -> str:
    url = urlsplit(value)
    if (
        url.scheme != "https"
        or not url.hostname
        or url.username
        or url.password
        or url.fragment
        or url.hostname in {"localhost", "127.0.0.1", "::1"}
    ):
        raise PreferenceValidationError("Configura una URL pública HTTPS válida.")
    return value


def build_preference(order, *, return_url: str, notification_url: str, now=None):
    """order debe proceder de la base de datos, nunca del cuerpo enviado por React."""
    if order.estado != "PENDIENTE_PAGO":
        raise PreferenceValidationError("El pedido no está pendiente de pago.")
    now = now or datetime.now(timezone.utc)
    if order.creado_en.tzinfo is None or now.tzinfo is None:
        raise PreferenceValidationError("Las fechas deben incluir zona horaria.")
    expires_at = order.creado_en + timedelta(minutes=15)
    if now >= expires_at:
        raise PreferenceValidationError("El plazo de pago del pedido terminó.")
    return_url = public_https_url(return_url)
    notification_url = public_https_url(notification_url)

    items = []
    total = Decimal(0)
    for detail in order.detalles:
        price = Decimal(detail.precio_unitario)
        quantity = detail.cantidad
        if (
            not price.is_finite()
            or price <= 0
            or price != price.to_integral_value()
            or type(quantity) is not int
            or quantity <= 0
        ):
            raise PreferenceValidationError(
                "Revisa el precio en pesos enteros y la cantidad del pedido."
            )
        subtotal = price * quantity
        if subtotal != detail.subtotal:
            raise PreferenceValidationError("El detalle del pedido no coincide.")
        total += subtotal
        items.append({
            "id": str(detail.producto_id),
            "title": detail.nombre,
            "quantity": quantity,
            "currency_id": "CLP",
            "unit_price": int(price),
        })
    if not items or total != order.total:
        raise PreferenceValidationError("El total del pedido no coincide.")

    return {
        "items": items,
        "external_reference": str(order.id),
        "back_urls": {
            "success": return_url,
            "pending": return_url,
            "failure": return_url,
        },
        "notification_url": notification_url,
        "auto_return": "approved",
        "expires": True,
        "expiration_date_from": now.isoformat(timespec="milliseconds"),
        "expiration_date_to": expires_at.isoformat(timespec="milliseconds"),
    }
