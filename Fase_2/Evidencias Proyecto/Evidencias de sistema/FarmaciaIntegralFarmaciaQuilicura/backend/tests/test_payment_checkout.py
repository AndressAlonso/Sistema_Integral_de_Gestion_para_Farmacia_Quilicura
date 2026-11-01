# ruff: noqa: F811
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from unittest.mock import Mock
from uuid import UUID, uuid4

import pytest
from test_e6_cart import cart, snapshot  # noqa: F401
from test_orders import order_payload

from app.models import Producto
from app.orders.models import PedidoOnline
from app.payments.client import MercadoPagoError
from app.payments.models import CheckoutMercadoPago


@pytest.fixture
def checkout(cart, monkeypatch):
    monkeypatch.setenv("MP_ACCESS_TOKEN", "token-ficticio")
    monkeypatch.setenv("MP_CHECKOUT_ENABLED", "true")
    monkeypatch.setenv("MP_PUBLIC_BASE_URL", "https://tienda.example")
    provider = Mock()
    provider.create_preference.return_value = {
        "id": "pref-" + uuid4().hex,
        "init_point": "https://www.mercadopago.cl/checkout/test",
    }
    monkeypatch.setattr("app.payments.service.MercadoPagoClient", lambda _: provider)
    with cart.factory.begin() as db:
        db.get(Producto, cart.cart_ids["product"]).precio_actual = Decimal(1000)
    data = order_payload(cart, quantity=1)
    data["expected_total"] = "1000"
    response = cart.client.post("/api/customers/orders", json=data)
    assert response.status_code == 201, response.text
    cart.payment_order = data
    cart.payment_provider = provider
    return cart


def pay(ctx, token=None, **kwargs):
    return ctx.client.post(
        "/api/customers/orders/" + ctx.payment_order["request_id"] + "/checkout",
        json={"request_token": token or ctx.payment_order["request_token"]},
        **kwargs,
    )


def test_saved_checkout_is_reused_without_stock_changes(checkout):
    before = snapshot(checkout)
    first = pay(checkout)
    assert first.status_code == 200, first.text
    assert pay(checkout).json() == first.json()
    assert checkout.payment_provider.create_preference.call_count == 1
    payload = checkout.payment_provider.create_preference.call_args.args[0]
    assert payload["items"][0]["unit_price"] == 1000
    assert payload["external_reference"] == checkout.payment_order["request_id"]
    assert snapshot(checkout) == before
    with checkout.factory() as db:
        identity = UUID(checkout.payment_order["request_id"])
        assert db.get(CheckoutMercadoPago, identity).estado == "LISTO"
        assert db.get(PedidoOnline, identity).estado == "PENDIENTE_PAGO"


def test_wrong_token_is_rejected(checkout):
    assert pay(checkout, token="x" * 64).status_code == 404
    checkout.payment_provider.create_preference.assert_not_called()


def test_foreign_origin_is_rejected(checkout):
    assert pay(checkout, headers={"Origin": "https://attacker.example"}).status_code == 403
    checkout.payment_provider.create_preference.assert_not_called()


def test_provider_failure_is_persisted_and_not_retried(checkout):
    checkout.payment_provider.create_preference.side_effect = MercadoPagoError("timeout")
    assert pay(checkout).status_code == 502
    assert pay(checkout).status_code == 409
    assert checkout.payment_provider.create_preference.call_count == 1
    with checkout.factory() as db:
        row = db.get(CheckoutMercadoPago, UUID(checkout.payment_order["request_id"]))
        assert row.estado == "INCIERTO" and row.checkout_url is None


def test_untrusted_payment_link_is_not_returned(checkout):
    checkout.payment_provider.create_preference.return_value["init_point"] = "https://attacker.example"
    response = pay(checkout)
    assert response.status_code == 502
    assert "attacker" not in response.text


@pytest.mark.parametrize("condition", ["cancelled", "expired", "creating"])
def test_unavailable_order_does_not_call_provider(checkout, condition):
    identity = UUID(checkout.payment_order["request_id"])
    with checkout.factory.begin() as db:
        order = db.get(PedidoOnline, identity)
        if condition == "cancelled":
            order.estado = "CANCELADO"
        elif condition == "expired":
            order.creado_en = datetime.now(timezone.utc) - timedelta(minutes=16)
        else:
            db.add(CheckoutMercadoPago(
                pedido_id=identity, estado="CREANDO", total=order.total,
                moneda="CLP", creado_en=order.creado_en,
                vence_en=order.creado_en + timedelta(minutes=15),
            ))
    assert pay(checkout).status_code == 409
    checkout.payment_provider.create_preference.assert_not_called()


def test_disabled_checkout_does_not_call_provider(checkout, monkeypatch):
    monkeypatch.setenv("MP_CHECKOUT_ENABLED", "false")
    assert pay(checkout).status_code == 503
    checkout.payment_provider.create_preference.assert_not_called()


def test_client_cannot_supply_amount(checkout):
    response = checkout.client.post(
        "/api/customers/orders/" + checkout.payment_order["request_id"] + "/checkout",
        json={"request_token": checkout.payment_order["request_token"], "total": 1},
    )
    assert response.status_code == 422
    checkout.payment_provider.create_preference.assert_not_called()


def test_logged_in_customer_cannot_use_guest_checkout(checkout):
    account = {
        "name": "Comprador QA", "email": checkout.suffix + "@example.com",
        "password": "Password-Only-QA-123!",
    }
    assert checkout.client.post("/api/customers/register", json=account).status_code == 201
    assert checkout.client.post("/api/customers/login", json={
        "email": account["email"], "password": account["password"],
    }).status_code == 200
    assert pay(checkout).status_code == 404
    checkout.payment_provider.create_preference.assert_not_called()


def test_registered_order_requires_its_customer_session(checkout):
    account = {
        "name": "Comprador QA", "email": checkout.suffix + "@example.com",
        "password": "Password-Only-QA-123!",
    }
    checkout.client.post("/api/customers/register", json=account)
    checkout.client.post("/api/customers/login", json={
        "email": account["email"], "password": account["password"],
    })
    data = order_payload(checkout, quantity=1)
    data.update(expected_total="1000", guest=None)
    assert checkout.client.post("/api/customers/orders", json=data).status_code == 201
    checkout.payment_order = data
    assert pay(checkout).status_code == 200
    checkout.client.post("/api/customers/logout")
    assert pay(checkout).status_code == 404
    assert checkout.payment_provider.create_preference.call_count == 1
