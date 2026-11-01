# ruff: noqa: F811
import hashlib
import hmac
from datetime import datetime, timedelta, timezone
from unittest.mock import Mock
from uuid import UUID, uuid4

import pytest
from sqlalchemy import func, select
from test_e6_cart import cart, snapshot  # noqa: F401
from test_payment_checkout import checkout, pay  # noqa: F401

from app.models import Venta, VentaDetalle
from app.orders.models import PedidoOnline, ReservaPedido
from app.payments.client import MercadoPagoError
from app.payments.models import CheckoutMercadoPago, PagoMercadoPago

SECRET = "webhook-qa-no-real"
PATH = "/api/payments/mercadopago/webhook"


@pytest.fixture
def webhook(checkout, monkeypatch):
    ctx = checkout
    monkeypatch.setenv("MP_WEBHOOK_SECRET", SECRET)
    assert pay(ctx).status_code == 200
    now = datetime.now(timezone.utc)
    ctx.mp_id = str(uuid4().int % (10**18))
    ctx.mp_data = {
        "id": int(ctx.mp_id),
        "collector_id": 999,
        "live_mode": False,
        "currency_id": "CLP",
        "transaction_amount": 1000,
        "transaction_amount_refunded": 0,
        "captured": True,
        "external_reference": ctx.payment_order["request_id"],
        "status": "approved",
        "date_last_updated": now.isoformat(),
        "date_approved": now.isoformat(),
        "order": {"id": 456, "type": "mercadopago"},
    }
    provider = Mock()
    provider.get_account.return_value = {
        "id": 999,
        "site_id": "MLC",
        "tags": ["test_user"],
    }
    provider.get_payment.return_value = ctx.mp_data
    provider.get_merchant_order.return_value = {
        "id": 456,
        "collector": {"id": 999},
        "external_reference": ctx.payment_order["request_id"],
        "preference_id": ctx.payment_provider.create_preference.return_value["id"],
        "payments": [{"id": int(ctx.mp_id)}],
    }
    ctx.webhook_provider = provider
    monkeypatch.setattr("app.payments.processor.MercadoPagoClient", lambda _: provider)
    return ctx


def notify(ctx, signature=None, **kwargs):
    manifest = f"id:{ctx.mp_id};request-id:qa-request;ts:1704908010;"
    digest = hmac.new(SECRET.encode(), manifest.encode(), hashlib.sha256).hexdigest()
    return ctx.client.post(
        PATH + "?data.id=" + ctx.mp_id,
        headers={
            "x-request-id": "qa-request",
            "x-signature": signature or f"ts=1704908010,v1={digest}",
        },
        **kwargs,
    )


def state(ctx):
    with ctx.factory() as db:
        order_id = UUID(ctx.payment_order["request_id"])
        payment = db.get(PagoMercadoPago, ctx.mp_id)
        return {
            "order": db.get(PedidoOnline, order_id).estado,
            "payment": payment.estado if payment else None,
            "review": payment.revision_motivo if payment else None,
            "sales": db.scalar(
                select(func.count())
                .select_from(Venta)
                .where(Venta.pedido_id == order_id)
            ),
            "active": db.scalar(
                select(func.count())
                .select_from(ReservaPedido)
                .where(
                    ReservaPedido.pedido_id == order_id, ReservaPedido.activa.is_(True)
                )
            ),
        }


def test_approved_repeated_creates_one_sale_and_preserves_stock(webhook):
    before = snapshot(webhook)
    assert notify(webhook).status_code == 200
    assert notify(webhook).json()["result"] == "duplicate"
    after = state(webhook)
    assert after["order"] == "PAGADO" and after["sales"] == 1 and after["active"] == 1
    assert snapshot(webhook) == before
    with webhook.factory() as db:
        sale = db.scalar(
            select(Venta).where(
                Venta.pedido_id == UUID(webhook.payment_order["request_id"])
            )
        )
        assert sale.usuario_id is None and sale.sesion_caja_id is None
        assert sale.medio_pago == "MERCADOPAGO" and sale.total == 1000
        assert (
            db.scalar(
                select(func.count())
                .select_from(VentaDetalle)
                .where(VentaDetalle.venta_id == sale.id)
            )
            == 1
        )


def test_invalid_signature_never_calls_provider(webhook):
    assert notify(webhook, signature="ts=1704908010,v1=" + "0" * 64).status_code == 401
    webhook.webhook_provider.get_account.assert_not_called()
    assert state(webhook)["payment"] is None


def test_ignores_forged_body_status(webhook):
    webhook.mp_data.update(status="pending", date_approved=None)
    assert (
        notify(
            webhook, json={"status": "approved", "data": {"id": "another"}}
        ).status_code
        == 200
    )
    assert state(webhook)["order"] == "PENDIENTE_PAGO" and state(webhook)["sales"] == 0


@pytest.mark.parametrize(
    "field,value",
    [
        ("transaction_amount", 999),
        ("transaction_amount", "NaN"),
        ("currency_id", "USD"),
        ("collector_id", 1),
        ("live_mode", True),
        ("id", 1),
        ("captured", False),
        ("date_approved", None),
        ("date_last_updated", "invalid"),
        ("status", "unknown"),
    ],
)
def test_mismatched_payment_is_rejected_without_changes(webhook, field, value):
    before = snapshot(webhook)
    webhook.mp_data[field] = value
    assert notify(webhook).status_code == 422
    assert state(webhook)["payment"] is None and state(webhook)["sales"] == 0
    assert snapshot(webhook) == before


def test_other_preference_is_rejected(webhook):
    webhook.webhook_provider.get_merchant_order.return_value["preference_id"] = "other"
    assert notify(webhook).status_code == 422
    assert state(webhook)["payment"] is None


@pytest.mark.parametrize("status", ["rejected", "cancelled"])
def test_rejection_releases_only_reservation_once(webhook, status):
    before = snapshot(webhook)
    webhook.mp_data.update(status=status, date_approved=None)
    assert notify(webhook).status_code == 200
    after = snapshot(webhook)
    assert [r.stock_fisico for r in before[0]] == [r.stock_fisico for r in after[0]]
    assert (
        sum(r.stock_reservado for r in before[0])
        - sum(r.stock_reservado for r in after[0])
        == 1
    )
    assert before[1] == after[1]
    assert state(webhook)["order"] == "CANCELADO" and state(webhook)["sales"] == 0
    assert state(webhook)["active"] == 0
    assert notify(webhook).status_code == 200 and snapshot(webhook) == after


@pytest.mark.parametrize("method", ["get_account", "get_payment", "get_merchant_order"])
def test_provider_error_does_not_ack_or_change_order(webhook, method):
    getattr(webhook.webhook_provider, method).side_effect = MercadoPagoError(
        "unavailable"
    )
    assert notify(webhook).status_code == 503
    assert (
        state(webhook)["order"] == "PENDIENTE_PAGO"
        and state(webhook)["payment"] is None
    )


def test_database_failure_rolls_back_payment_and_sale(webhook, monkeypatch):
    def broken(*args):
        raise RuntimeError("failure")

    monkeypatch.setattr("app.payments.processor.register_sale", broken)
    assert notify(webhook).status_code == 500
    assert state(webhook)["payment"] is None and state(webhook)["sales"] == 0
    assert state(webhook)["order"] == "PENDIENTE_PAGO"


def test_late_approval_is_recorded_for_review_without_sale(webhook):
    identity = UUID(webhook.payment_order["request_id"])
    with webhook.factory.begin() as db:
        order = db.get(PedidoOnline, identity)
        order.creado_en -= timedelta(minutes=20)
        checkout_row = db.get(CheckoutMercadoPago, identity)
        checkout_row.creado_en -= timedelta(minutes=20)
        checkout_row.vence_en -= timedelta(minutes=20)
    assert notify(webhook).json()["result"] == "review"
    assert state(webhook)["order"] == "CANCELADO" and state(webhook)["sales"] == 0
    assert state(webhook)["review"] == "APROBADO_FUERA_DE_PLAZO"


def test_approval_of_cancelled_order_does_not_reactivate(webhook):
    identity = UUID(webhook.payment_order["request_id"])
    with webhook.factory.begin() as db:
        db.get(PedidoOnline, identity).estado = "CANCELADO"
    assert notify(webhook).json()["result"] == "review"
    assert state(webhook)["order"] == "CANCELADO" and state(webhook)["sales"] == 0


def test_second_approved_payment_does_not_duplicate_sale(webhook):
    assert notify(webhook).status_code == 200
    webhook.mp_id = str(int(webhook.mp_id) + 1)
    webhook.mp_data["id"] = int(webhook.mp_id)
    webhook.webhook_provider.get_merchant_order.return_value["payments"].append(
        {"id": int(webhook.mp_id)}
    )
    assert notify(webhook).json()["result"] == "review"
    assert (
        state(webhook)["sales"] == 1
        and state(webhook)["review"] == "SEGUNDO_PAGO_APROBADO"
    )


def test_refund_blocks_order_without_erasing_sale_or_changing_stock(webhook):
    assert notify(webhook).status_code == 200
    before = snapshot(webhook)
    webhook.mp_data.update(
        status="refunded",
        date_last_updated=(
            datetime.now(timezone.utc) + timedelta(seconds=1)
        ).isoformat(),
    )
    assert notify(webhook).json()["result"] == "review"
    assert state(webhook)["order"] == "REVISION_PAGO" and state(webhook)["sales"] == 1
    assert snapshot(webhook) == before


def test_older_provider_response_does_not_regress_approved_order(webhook):
    assert notify(webhook).status_code == 200
    webhook.mp_data.update(
        status="pending", date_approved=None, date_last_updated="2020-01-01T00:00:00Z"
    )
    assert notify(webhook).json()["result"] == "older"
    assert (
        state(webhook)["order"] == "PAGADO" and state(webhook)["payment"] == "approved"
    )


def test_partial_refund_blocks_order_for_review(webhook):
    assert notify(webhook).status_code == 200
    webhook.mp_data.update(
        transaction_amount_refunded=100,
        date_last_updated=(
            datetime.now(timezone.utc) + timedelta(seconds=1)
        ).isoformat(),
    )
    assert notify(webhook).json()["result"] == "review"
    assert state(webhook)["order"] == "REVISION_PAGO" and state(webhook)["sales"] == 1


def test_online_sale_is_not_exposed_as_pos_receipt(webhook):
    from types import SimpleNamespace

    from app.pos.repository import PosRepository
    from app.pos.service import PosError, PosService

    assert notify(webhook).status_code == 200
    actor = SimpleNamespace(permissions={"pos.operar"}, roles={"ADMINISTRADOR"})
    service = PosService(PosRepository(webhook.factory))
    with webhook.factory() as db:
        sale_id = db.scalar(
            select(Venta.id).where(
                Venta.pedido_id == UUID(webhook.payment_order["request_id"])
            )
        )
    assert all(row["id"] != str(sale_id) for row in service.list_sales(actor)["sales"])
    with pytest.raises(PosError) as error:
        service.receipt(actor, sale_id)
    assert error.value.status == 404


@pytest.mark.parametrize("status", ["PAGADO", "REVISION_PAGO"])
def test_branch_with_paid_or_review_order_cannot_close(webhook, status):
    from app.branches.repository import BranchPendingOrders, PostgresBranchRepository

    assert notify(webhook).status_code == 200
    with webhook.factory.begin() as db:
        db.get(PedidoOnline, UUID(webhook.payment_order["request_id"])).estado = status
    with pytest.raises(BranchPendingOrders):
        PostgresBranchRepository(webhook.factory).deactivate(webhook.cart_ids["destination"])
