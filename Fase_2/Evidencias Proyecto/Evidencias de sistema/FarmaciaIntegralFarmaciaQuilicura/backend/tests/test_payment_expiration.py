# ruff: noqa: F811
import asyncio
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from unittest.mock import Mock
from uuid import UUID

import pytest
from fastapi import HTTPException
from test_e6_cart import cart, snapshot  # noqa: F401
from test_orders import order_payload
from test_payment_checkout import checkout  # noqa: F401
from test_payment_webhook import state, webhook  # noqa: F401

from app.orders.models import PedidoOnline
from app.payments.client import MercadoPagoError
from app.payments.config import PaymentSettings
from app.payments.expiration import PaymentExpirationService
from app.payments.models import CheckoutMercadoPago
from app.payments.processor import PaymentVerificationError
from app.payments.worker import payment_expiration_worker


def expired(ctx):
    identity = UUID(ctx.payment_order["request_id"])
    with ctx.factory.begin() as db:
        order = db.get(PedidoOnline, identity)
        order.creado_en = datetime.now(timezone.utc) - timedelta(minutes=16)
        checkout_row = db.get(CheckoutMercadoPago, identity)
        if checkout_row:
            checkout_row.creado_en = order.creado_en
            checkout_row.vence_en = order.creado_en + timedelta(minutes=15)
    return identity


def service(ctx):
    return PaymentExpirationService(
        ctx.factory, PaymentSettings(), ctx.webhook_provider
    )


def test_unpaid_expiration_releases_reservation_once(webhook):
    identity = expired(webhook)
    webhook.webhook_provider.search_payments.return_value = []
    before = snapshot(webhook)
    job = service(webhook)
    assert job.expire(identity) == "cancelled"
    after = snapshot(webhook)
    assert state(webhook)["order"] == "CANCELADO"
    assert state(webhook)["active"] == 0 and state(webhook)["sales"] == 0
    assert before[1] == after[1]
    assert [r.stock_fisico for r in before[0]] == [r.stock_fisico for r in after[0]]
    assert (
        sum(r.stock_reservado for r in before[0])
        - sum(r.stock_reservado for r in after[0])
        == 1
    )
    assert job.expire(identity) == "ignored"
    assert snapshot(webhook) == after


def test_order_without_checkout_expires_without_provider_call(checkout):
    identity = expired(checkout)
    provider = Mock()
    job = PaymentExpirationService(checkout.factory, PaymentSettings(), provider)
    assert job.expire(identity) == "cancelled"
    assert provider.mock_calls == []


def test_nonexpired_order_is_not_touched(webhook):
    before = snapshot(webhook)
    assert (
        service(webhook).expire(UUID(webhook.payment_order["request_id"])) == "ignored"
    )
    assert snapshot(webhook) == before
    webhook.webhook_provider.search_payments.assert_not_called()


def test_missing_webhook_approval_is_recovered(webhook):
    identity = expired(webhook)
    approved = datetime.now(timezone.utc) - timedelta(minutes=2)
    webhook.mp_data.update(date_approved=approved.isoformat())
    webhook.webhook_provider.search_payments.return_value = [dict(webhook.mp_data)]
    before = snapshot(webhook)
    assert service(webhook).expire(identity) == "paid"
    assert state(webhook)["order"] == "PAGADO" and state(webhook)["sales"] == 1
    assert snapshot(webhook) == before


@pytest.mark.parametrize("method", ["get_account", "search_payments", "get_payment"])
def test_provider_outage_preserves_reservation(webhook, method):
    identity = expired(webhook)
    # Otro pedido vencido reproduce una BD de desarrollo con datos anteriores.
    unrelated = order_payload(webhook, quantity=1)
    unrelated["expected_total"] = "1000"
    assert (
        webhook.client.post("/api/customers/orders", json=unrelated).status_code == 201
    )
    with webhook.factory.begin() as db:
        db.get(PedidoOnline, UUID(unrelated["request_id"])).creado_en = datetime.now(
            timezone.utc
        ) - timedelta(minutes=20)
    webhook.webhook_provider.search_payments.return_value = [dict(webhook.mp_data)]
    getattr(webhook.webhook_provider, method).side_effect = MercadoPagoError("timeout")
    before = snapshot(webhook)
    expected_error = HTTPException if method == "get_payment" else MercadoPagoError
    with pytest.raises(expected_error) as error:
        service(webhook).expire(identity)
    if method == "get_payment":
        assert error.value.status_code == 503
    with webhook.factory() as db:
        assert (
            db.get(PedidoOnline, UUID(unrelated["request_id"])).estado
            == "PENDIENTE_PAGO"
        )
    assert state(webhook)["order"] == "PENDIENTE_PAGO" and snapshot(webhook) == before


def test_wrong_account_keeps_reservations(webhook):
    identity = expired(webhook)
    webhook.webhook_provider.get_account.return_value["site_id"] = "MLA"
    with pytest.raises(PaymentVerificationError):
        service(webhook).expire(identity)
    assert state(webhook)["order"] == "PENDIENTE_PAGO"


def test_new_payment_between_queries_defers_expiration(webhook):
    identity = expired(webhook)
    webhook.webhook_provider.search_payments.side_effect = [
        [],
        [{"id": webhook.mp_id, "status": "pending"}],
    ]
    assert service(webhook).expire(identity) == "retry"
    assert state(webhook)["order"] == "PENDIENTE_PAGO" and state(webhook)["active"] == 1


def test_new_approval_between_queries_defers_expiration(webhook):
    identity = expired(webhook)
    pending = dict(webhook.mp_data, status="pending", date_approved=None)
    webhook.webhook_provider.get_payment.return_value = pending
    webhook.webhook_provider.search_payments.side_effect = [
        [pending],
        [dict(webhook.mp_data)],
    ]
    assert service(webhook).expire(identity) == "retry"
    assert state(webhook)["order"] == "PENDIENTE_PAGO" and state(webhook)["active"] == 1


def test_pending_payment_expires_after_provider_verification(webhook):
    identity = expired(webhook)
    webhook.mp_data.update(status="pending", date_approved=None)
    webhook.webhook_provider.search_payments.return_value = [dict(webhook.mp_data)]
    assert service(webhook).expire(identity) == "cancelled"
    assert state(webhook)["payment"] == "pending" and state(webhook)["sales"] == 0


def test_approved_payment_is_processed_before_rejected_attempt(webhook):
    identity = expired(webhook)
    approved = datetime.now(timezone.utc) - timedelta(minutes=2)
    webhook.mp_data["date_approved"] = approved.isoformat()
    other = dict(
        webhook.mp_data,
        id=int(webhook.mp_id) + 1,
        status="rejected",
        date_approved=None,
    )
    webhook.webhook_provider.search_payments.return_value = [
        other,
        dict(webhook.mp_data),
    ]
    webhook.webhook_provider.get_payment.side_effect = lambda key: (
        webhook.mp_data if key == webhook.mp_id else other
    )
    webhook.webhook_provider.get_merchant_order.return_value["payments"].append(
        {"id": other["id"]}
    )
    assert service(webhook).expire(identity) == "paid"
    assert state(webhook)["order"] == "PAGADO" and state(webhook)["sales"] == 1


def test_unresolved_preference_with_payment_keeps_reservations(webhook):
    identity = expired(webhook)
    with webhook.factory.begin() as db:
        row = db.get(CheckoutMercadoPago, identity)
        row.estado, row.preferencia_id, row.checkout_url = "INCIERTO", None, None
    webhook.webhook_provider.search_payments.return_value = [dict(webhook.mp_data)]
    with pytest.raises(HTTPException) as error:
        service(webhook).expire(identity)
    assert error.value.status_code == 503
    assert state(webhook)["order"] == "PENDIENTE_PAGO"


def test_worker_does_not_start_when_disabled(monkeypatch):
    monkeypatch.setattr(
        "app.payments.worker.PaymentWorkerSettings",
        lambda: SimpleNamespace(expiration_enabled=False),
    )
    constructor = Mock()
    monkeypatch.setattr("app.payments.worker.PaymentExpirationService", constructor)

    async def exercise():
        async with payment_expiration_worker(None):
            pass

    asyncio.run(exercise())
    constructor.assert_not_called()


def test_worker_runs_and_finishes_current_cycle_on_shutdown(monkeypatch):
    monkeypatch.setattr(
        "app.payments.worker.PaymentWorkerSettings",
        lambda: SimpleNamespace(expiration_enabled=True),
    )
    monkeypatch.setattr("app.payments.worker.PaymentSettings", lambda: object())
    called = Mock(return_value={"cancelled": 0})
    monkeypatch.setattr(
        "app.payments.worker.PaymentExpirationService",
        lambda *args: SimpleNamespace(run_once=called),
    )

    async def exercise():
        async with payment_expiration_worker(None):
            for _ in range(100):
                if called.called:
                    break
                await asyncio.sleep(0.01)
        assert called.call_count == 1
        assert called.call_args.args[0].is_set()

    asyncio.run(exercise())
