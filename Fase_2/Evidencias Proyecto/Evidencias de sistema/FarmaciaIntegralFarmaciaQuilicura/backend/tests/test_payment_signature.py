import hashlib
import hmac

import pytest
from fastapi import Request
from pydantic import SecretStr, ValidationError

from app.payments.config import PaymentSettings
from app.payments.signature import (
    InvalidWebhookSignature,
    WebhookNotConfigured,
    verified_payment_id,
)

SECRET = SecretStr("clave-ficticia-exclusivamente-para-tests")
MANIFEST = b"id:123456789;request-id:request-123;ts:1704908010;"
DIGEST = hmac.new(
    SECRET.get_secret_value().encode(), MANIFEST, hashlib.sha256
).hexdigest()
SIGNATURE = f"ts=1704908010,v1={DIGEST}"


def notification(
    query=b"data.id=123456789", signature=SIGNATURE, request_id="request-123"
):
    headers = []
    if signature is not None:
        headers.append((b"x-signature", signature.encode()))
    if request_id is not None:
        headers.append((b"x-request-id", request_id.encode()))
    return Request({"type": "http", "query_string": query, "headers": headers})


def test_accepts_signed_id_without_trusting_json_body():
    assert verified_payment_id(notification(), SECRET) == "123456789"


def test_accepts_authenticated_retry_without_claiming_payment_is_approved():
    # Una firma antigua sigue autenticando el ID; no es un estado del pago.
    assert verified_payment_id(notification(), SECRET) == "123456789"


@pytest.mark.parametrize(
    "query",
    [
        b"",
        b"data.id=",
        b"data.id=987654321",
        b"data.id=123456789&data.id=123456789",
        b"data.id=123456789&data.id=987654321",
        b"id=123456789",
        b"data.id=../payments",
        b"data.id=123%3Brequest-id%3Aevil",
    ],
)
def test_rejects_missing_modified_or_ambiguous_id(query):
    with pytest.raises(InvalidWebhookSignature):
        verified_payment_id(notification(query=query), SECRET)


@pytest.mark.parametrize(
    "signature",
    [
        None,
        "",
        "ts=1704908010",
        f"v1={DIGEST}",
        f"ts=no,v1={DIGEST}",
        f"ts=1704908011,v1={DIGEST}",
        f"ts=1704908010,ts=1704908010,v1={DIGEST}",
        "ts=1704908010,v1=" + "0" * 64,
        "ts=1704908010,v1=xyz",
        SIGNATURE + ",invalid",
        "x" * 2049,
    ],
)
def test_rejects_invalid_signature(signature):
    with pytest.raises(InvalidWebhookSignature):
        verified_payment_id(notification(signature=signature), SECRET)


@pytest.mark.parametrize(
    "request_id", [None, "", "changed", "request-123;ts:1704908010"]
)
def test_rejects_missing_or_modified_request_id(request_id):
    with pytest.raises(InvalidWebhookSignature):
        verified_payment_id(notification(request_id=request_id), SECRET)


def test_rejects_wrong_secret():
    with pytest.raises(InvalidWebhookSignature):
        verified_payment_id(notification(), SecretStr("otra-clave"))


@pytest.mark.parametrize("secret", [None, SecretStr("")])
def test_missing_configuration_fails_closed(secret):
    with pytest.raises(WebhookNotConfigured):
        verified_payment_id(notification(), secret)


@pytest.mark.parametrize("header", [b"x-signature", b"x-request-id"])
def test_rejects_duplicate_headers(header):
    request = notification()
    request.scope["headers"].append((header, b"duplicate"))
    with pytest.raises(InvalidWebhookSignature):
        verified_payment_id(request, SECRET)


def test_accepts_multiple_v1_signatures_when_one_matches():
    signature = f"ts=1704908010,v1={'0' * 64},v1={DIGEST}"
    assert verified_payment_id(notification(signature=signature), SECRET) == "123456789"


def test_secret_is_loaded_without_exposing_it(monkeypatch):
    monkeypatch.setenv("MP_ACCESS_TOKEN", "fake-token")
    monkeypatch.setenv("MP_WEBHOOK_SECRET", "private-webhook-value")
    settings = PaymentSettings(_env_file=None)
    assert settings.webhook_secret.get_secret_value() == "private-webhook-value"
    assert "private-webhook-value" not in repr(settings)


@pytest.mark.parametrize("value", ["", "   ", "PEGA_AQUI_LA_CLAVE_SECRETA"])
def test_rejects_empty_or_placeholder_secret(value):
    with pytest.raises(ValidationError):
        PaymentSettings(_env_file=None, access_token="fake", webhook_secret=value)
