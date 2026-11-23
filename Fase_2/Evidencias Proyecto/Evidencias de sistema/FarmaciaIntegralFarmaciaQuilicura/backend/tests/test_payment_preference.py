from datetime import datetime, timedelta, timezone
from decimal import Decimal
from types import SimpleNamespace
from uuid import uuid4

import pytest

from app.payments.preference import PreferenceValidationError, build_preference

NOW = datetime(2026, 10, 18, 18, 0, tzinfo=timezone.utc)


@pytest.fixture
def order():
    return SimpleNamespace(
        id=uuid4(), estado="PENDIENTE_PAGO", creado_en=NOW,
        total=Decimal("3980.00"), detalles=[SimpleNamespace(
            producto_id=uuid4(), nombre="Producto de prueba", cantidad=2,
            precio_unitario=Decimal("1990.00"), subtotal=Decimal("3980.00"),
        )],
    )


def build(order, **overrides):
    options = {
        "return_url": "https://tienda.example/pedido",
        "notification_url": "https://tienda.example/api/payments/webhook",
        "now": NOW,
    }
    options.update(overrides)
    return build_preference(order, **options)


def test_uses_saved_price_and_reference(order):
    payload = build(order)
    assert payload["external_reference"] == str(order.id)
    assert payload["items"][0]["unit_price"] == 1990
    assert payload["items"][0]["quantity"] == 2
    assert payload["items"][0]["currency_id"] == "CLP"
    assert payload["expiration_date_to"] == "2026-10-18T18:15:00.000+00:00"
    assert "payer" not in payload


def test_does_not_extend_deadline(order):
    payload = build(order, now=NOW + timedelta(minutes=10))
    assert payload["expiration_date_to"] == "2026-10-18T18:15:00.000+00:00"


@pytest.mark.parametrize("minutes", [15, 16])
def test_expired_order(order, minutes):
    with pytest.raises(PreferenceValidationError, match="plazo"):
        build(order, now=NOW + timedelta(minutes=minutes))


def test_cancelled_order(order):
    order.estado = "CANCELADO"
    with pytest.raises(PreferenceValidationError, match="pendiente"):
        build(order)


def test_modified_total(order):
    order.total = Decimal(1)
    with pytest.raises(PreferenceValidationError, match="total"):
        build(order)


def test_modified_subtotal(order):
    order.detalles[0].subtotal = Decimal(1)
    with pytest.raises(PreferenceValidationError, match="detalle"):
        build(order)


@pytest.mark.parametrize("price", ["0", "-1", "1990.50", "NaN", "Infinity"])
def test_invalid_price_is_not_rounded(order, price):
    order.detalles[0].precio_unitario = Decimal(price)
    with pytest.raises(PreferenceValidationError, match="precio"):
        build(order)


@pytest.mark.parametrize("url", ["http://tienda.example", "https://localhost", "https://127.0.0.1", "https://user:pass@tienda.example", "https://tienda.example/#secret"])
def test_invalid_return_url(order, url):
    with pytest.raises(PreferenceValidationError, match="HTTPS"):
        build(order, return_url=url)
