"""E7-H2: valida el ID firmado; el estado se consulta luego al proveedor."""

import hashlib
import hmac
import re

from fastapi import Request
from pydantic import SecretStr


class InvalidWebhookSignature(ValueError):
    """Notificación ausente, ambigua o no autenticada."""


class WebhookNotConfigured(RuntimeError):
    """No se configuró la clave privada del webhook."""


def verified_payment_id(request: Request, secret: SecretStr | None) -> str:
    """Devuelve exclusivamente el data.id autenticado de la URL.

    No confía en el cuerpo JSON ni confirma pagos. Los reintentos legítimos
    pueden llegar tarde: la idempotencia y el estado actual se comprobarán
    en el procesador, consultando la API del proveedor.
    """
    if secret is None or not secret.get_secret_value().strip():
        raise WebhookNotConfigured("Configura MP_WEBHOOK_SECRET.")

    ids = request.query_params.getlist("data.id")
    signatures = request.headers.getlist("x-signature")
    request_ids = request.headers.getlist("x-request-id")
    if len(ids) != 1 or len(signatures) != 1 or len(request_ids) != 1:
        raise InvalidWebhookSignature("Notificación no autenticada.")

    payment_id, signature, request_id = ids[0], signatures[0], request_ids[0]
    # Este módulo recibe el tópico payment de Preferences API: ID numérico.
    if not re.fullmatch(r"[0-9]{1,30}", payment_id):
        raise InvalidWebhookSignature("Notificación no autenticada.")
    if not re.fullmatch(r"[A-Za-z0-9_-]{1,200}", request_id):
        raise InvalidWebhookSignature("Notificación no autenticada.")
    if len(signature) > 2048:
        raise InvalidWebhookSignature("Notificación no autenticada.")

    timestamps: list[str] = []
    hashes: list[str] = []
    for part in signature.split(","):
        key, separator, value = part.strip().partition("=")
        if not separator:
            raise InvalidWebhookSignature("Notificación no autenticada.")
        key, value = key.strip().lower(), value.strip()
        if key == "ts":
            timestamps.append(value)
        elif key == "v1":
            hashes.append(value)

    if len(timestamps) != 1 or not hashes:
        raise InvalidWebhookSignature("Notificación no autenticada.")
    timestamp = timestamps[0]
    if not re.fullmatch(r"[0-9]{1,20}", timestamp) or not all(
        re.fullmatch(r"[a-fA-F0-9]{64}", value) for value in hashes
    ):
        raise InvalidWebhookSignature("Notificación no autenticada.")

    manifest = f"id:{payment_id};request-id:{request_id};ts:{timestamp};"
    expected = hmac.new(
        secret.get_secret_value().encode("utf-8"),
        manifest.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()
    if not any(hmac.compare_digest(expected, value.lower()) for value in hashes):
        raise InvalidWebhookSignature("Notificación no autenticada.")
    return payment_id
