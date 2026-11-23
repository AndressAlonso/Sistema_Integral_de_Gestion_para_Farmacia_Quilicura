"""E7-H2/H3/H4: pago verificado conectado con traslados y preparación."""
# ruff: noqa: F811
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from uuid import UUID

import pytest
from app.models import EventoAuditoria, Transferencia
from app.orders.models import PedidoOnline
from app.orders.preparation import PreparationService
from app.transfers.repository import TransferRepository
from app.transfers.schemas import ReceiveTransfer
from app.transfers.service import TransferError, TransferService
from sqlalchemy import func, select
from test_e6_cart import cart, snapshot  # noqa: F401
from test_payment_checkout import checkout, pay  # noqa: F401
from test_payment_webhook import notify, state, webhook  # noqa: F401


def actor(ctx):
    return SimpleNamespace(name="Administrador QA", id=ctx.ids["admin"], branch_id=ctx.cart_ids["destination"],
        is_active=True, roles=["ADMINISTRADOR"], permissions=[
            "pedidos.consultar", "pedidos.preparar", "transferencias.consultar",
            "transferencias.despachar", "transferencias.recibir"])


def needs_transfer(ctx):
    # El stock ya reservado existe en origen; cambiar el retiro antes de pagar
    # permite ejercitar exactamente el webhook firmado de la fixture.
    with ctx.factory.begin() as db:
        db.get(PedidoOnline, UUID(ctx.payment_order["request_id"])).sucursal_id = ctx.ids["branch"]


def test_payment_generates_transfer_once_then_prepares(webhook):
    ctx = webhook
    needs_transfer(ctx)
    identity = UUID(ctx.payment_order["request_id"])
    before = snapshot(ctx)
    assert notify(ctx).status_code == 200
    assert notify(ctx).json()["result"] == "duplicate"
    assert state(ctx)["sales"] == 1 and snapshot(ctx)[:3] == before[:3]
    with ctx.factory() as db:
        transfers = list(db.scalars(select(Transferencia).where(Transferencia.pedido_id == identity)))
        assert len(transfers) == 1
        transfer_id = transfers[0].id
        assert transfers[0].estado == "AUTORIZADA"
        assert db.scalar(select(func.count()).select_from(EventoAuditoria).where(
            EventoAuditoria.accion == "E7-H2_PAGO_VERIFICADO",
            EventoAuditoria.referencia_historica == f"Pedido {identity}")) == 1
    user = actor(ctx)
    preparation = PreparationService(ctx.factory)
    assert preparation.get(user, identity)["history"][0]["status"] == "PAGADO"
    preparation.change(user, identity, "preparation", "PAGADO")
    from fastapi import HTTPException
    with pytest.raises(HTTPException):
        preparation.change(user, identity, "ready", "EN_PREPARACION")
    transfers_service = TransferService(TransferRepository(ctx.factory))
    transfers_service.change(user, transfer_id, "dispatch")
    transfers_service.change(user, transfer_id, "receive", ReceiveTransfer(items=[
        {"product_id": ctx.cart_ids["product"], "quantity": 1}]))
    assert preparation.change(user, identity, "ready", "EN_PREPARACION")["status"] == "LISTO_PARA_RETIRO"
    ctx.mp_data["date_last_updated"] = (datetime.now(timezone.utc) + timedelta(seconds=1)).isoformat()
    assert notify(ctx).status_code == 200
    assert state(ctx)["order"] == "LISTO_PARA_RETIRO" and state(ctx)["sales"] == 1


def test_review_blocks_transfer_and_preparation_and_can_be_filtered(webhook):
    ctx = webhook
    needs_transfer(ctx)
    identity = UUID(ctx.payment_order["request_id"])
    assert notify(ctx).status_code == 200
    ctx.mp_data.update(status="refunded", date_last_updated=(datetime.now(timezone.utc) + timedelta(seconds=1)).isoformat())
    assert notify(ctx).status_code == 200
    user = actor(ctx)
    preparation = PreparationService(ctx.factory)
    assert preparation.get(user, identity)["actions"] == []
    results = preparation.list(user, "REVISION_PAGO", None, 1, 100)
    assert any(str(row["id"]) == str(identity) for row in results["orders"])
    with ctx.factory() as db:
        transfer_id = db.scalar(select(Transferencia.id).where(Transferencia.pedido_id == identity))
    with pytest.raises(TransferError):
        TransferService(TransferRepository(ctx.factory)).change(user, transfer_id, "dispatch")


def test_transfer_failure_rolls_back_payment_sale_and_audit(webhook, monkeypatch):
    def broken(*args):
        raise RuntimeError("fallo transaccional")
    monkeypatch.setattr("app.payments.processor.generate_order_transfers", broken)
    assert notify(webhook).status_code == 500
    assert state(webhook)["sales"] == 0 and state(webhook)["payment"] is None
    assert state(webhook)["order"] == "PENDIENTE_PAGO"
