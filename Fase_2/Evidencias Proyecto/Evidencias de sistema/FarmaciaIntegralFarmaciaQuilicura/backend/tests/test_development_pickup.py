"""Simulated sale supports the entire local workflow, never production."""
from uuid import UUID

import pytest
from app.models import Venta
from app.orders.fulfillment_models import RetiroPedido
from app.orders.models import PedidoOnline
from app.orders.pickup import PickupService, paid_sale
from app.payments.models import PagoMercadoPago
from fastapi import HTTPException
from sqlalchemy import func, select
from test_e6_cart import cart, snapshot  # noqa: F401
from test_order_preparation import preparation, receive, transition  # noqa: F401
from test_order_transfers import online, pay  # noqa: F401


def test_simulated_payment_to_single_pickup(preparation):  # noqa: F811
    ctx = preparation
    paid = pay(ctx)
    assert paid.status_code == 200, paid.text
    assert pay(ctx).json()["changed"] is False
    receive(ctx, UUID(paid.json()["transfer_ids"][0]))
    assert transition(ctx, "preparation", "PAGADO").status_code == 200
    assert transition(ctx, "ready", "EN_PREPARACION").status_code == 200
    with ctx.factory() as db:
        code = db.get(RetiroPedido, ctx.order_id).codigo
        sale = paid_sale(db, db.get(PedidoOnline, ctx.order_id))
        assert sale.medio_pago == "SIMULADO"
        assert db.scalar(select(func.count()).select_from(Venta).where(Venta.pedido_id == ctx.order_id)) == 1
        assert db.scalar(select(func.count()).select_from(PagoMercadoPago).where(PagoMercadoPago.pedido_id == ctx.order_id)) == 0
    ctx.actor.name = "Test operator"
    ctx.actor.permissions += ["pedidos.consultar", "pedidos.retirar"]
    service = PickupService(ctx.factory)
    before = snapshot(ctx)
    ctx.app.state.settings.app_environment = "production"
    with pytest.raises(HTTPException):
        service.process(ctx.actor, code, ctx.order_id)
    assert pay(ctx).status_code == 404
    assert snapshot(ctx) == before
    ctx.app.state.settings.app_environment = "development"
    assert service.process(ctx.actor, code)["status"] == "LISTO_PARA_RETIRO"
    assert snapshot(ctx) == before
    assert service.process(ctx.actor, code, ctx.order_id)["status"] == "RETIRADO"
    after = snapshot(ctx)
    with pytest.raises(HTTPException):
        service.process(ctx.actor, code, ctx.order_id)
    assert snapshot(ctx) == after


def test_legacy_simulation_is_listed_and_completed_once(online):  # noqa: F811
    from app.models import EventoAuditoria
    with online.factory.begin() as db:
        order = db.get(PedidoOnline, online.order_id)
        order.estado = "PAGADO"
        db.add(EventoAuditoria(origen_actor="SIMULACION_DESARROLLO", accion="E7-H3_PAGO_SIMULADO",
            referencia_historica=f"Pedido {order.id}", usuario_id=online.actor.id,
            sucursal_id=order.sucursal_id, datos_cambio={"resultado": "PAGADO", "simulado": True}))
    response = online.client.get("/api/orders/development/orders")
    assert response.status_code == 200, response.text
    assert str(online.order_id) in [o["id"] for o in response.json()["orders"]]
    response = pay(online)
    assert response.status_code == 200, response.text
    assert response.json()["changed"]
    assert not pay(online).json()["changed"]
    with online.factory() as db:
        assert paid_sale(db, db.get(PedidoOnline, online.order_id)).medio_pago == "SIMULADO"
