"""E7-H4: aceptación, permisos, historial e inventario; transacciones con rollback."""
from datetime import datetime, timezone
from uuid import UUID

import pytest
from sqlalchemy import select
from test_e6_cart import cart  # noqa: F401
from test_order_transfers import online, pay  # noqa: F401

from app.models import (
    EventoAuditoria,
    InventarioSucursal,
    LoteInventario,
    Permiso,
    Rol,
    UsuarioInterno,
)
from app.orders.models import PedidoOnline, ReservaPedido
from app.transfers.repository import TransferRepository
from app.transfers.schemas import ReceiveTransfer
from app.transfers.service import TransferService


@pytest.fixture
def preparation(online):  # noqa: F811
    with online.factory.begin() as db:
        user = db.get(UsuarioInterno, online.ids["admin"])
        role = next(r for r in user.roles if r.codigo == "ADMINISTRADOR")
        for code in ("pedidos.consultar", "pedidos.preparar"):
            permission = db.scalar(select(Permiso).where(Permiso.codigo == code))
            if permission is None:
                permission = Permiso(codigo=code, descripcion=code)
                db.add(permission)
            if permission not in role.permisos:
                role.permisos.append(permission)
    return online


def transition(ctx, action, state):
    return ctx.client.post(f"/api/orders/{ctx.order_id}/{action}", json={"expected_state": state})


def receive(ctx, transfer_id):
    service = TransferService(TransferRepository(ctx.factory))
    service.change(ctx.actor, transfer_id, "dispatch")
    service.change(ctx.actor, transfer_id, "receive", ReceiveTransfer(items=[
        {"product_id": ctx.cart_ids["product"], "quantity": 2}]))


def test_preparation_with_transfer_then_ready_and_idempotent(preparation):
    ctx = preparation
    payment = pay(ctx).json()
    transfer_id = UUID(payment["transfer_ids"][0])
    assert transition(ctx, "ready", "PAGADO").status_code == 409
    response = transition(ctx, "preparation", "PAGADO")
    assert response.status_code == 200, response.text
    assert response.json()["status"] == "EN_PREPARACION"
    assert response.json()["ready_blocked_reason"] and "ready" not in response.json()["actions"]
    assert transition(ctx, "preparation", "PAGADO").status_code == 200
    assert transition(ctx, "ready", "EN_PREPARACION").status_code == 409
    # El simulador no debe degradar la preparación ni duplicar transferencias.
    assert pay(ctx).json()["order"]["status"] == "EN_PREPARACION"
    receive(ctx, transfer_id)
    response = transition(ctx, "ready", "EN_PREPARACION")
    assert response.status_code == 200, response.text
    assert response.json()["status"] == "LISTO_PARA_RETIRO"
    assert response.json()["actions"] == []
    assert transition(ctx, "ready", "EN_PREPARACION").status_code == 200
    assert transition(ctx, "preparation", "PAGADO").status_code == 409
    with ctx.factory() as db:
        events = list(db.scalars(select(EventoAuditoria).where(
            EventoAuditoria.accion == "E7-H4_ESTADO",
            EventoAuditoria.referencia_historica == f"Pedido {ctx.order_id}").order_by(EventoAuditoria.secuencia)))
        assert len(events) == 2
        assert [e.datos_cambio["nuevo"] for e in events] == ["EN_PREPARACION", "LISTO_PARA_RETIRO"]
        assert all(e.usuario_id == ctx.ids["admin"] and e.ocurrido_en for e in events)
        inv = db.get(InventarioSucursal, ctx.cart_ids["destination_inventory"])
        assert (inv.stock_fisico, inv.stock_reservado) == (5, 5)
    assert len(response.json()["history"]) == 3
    assert "clave_hash" not in response.text and "solicitud_hash" not in response.text


@pytest.mark.parametrize("cancel", [False, True])
def test_unpaid_or_cancelled_cannot_prepare(preparation, cancel):
    if cancel:
        pay(preparation, "failed")
    assert transition(preparation, "preparation", "PAGADO").status_code == 409


@pytest.mark.parametrize("problem", ["missing", "expired", "inactive", "physical"])
def test_stock_problem_prevents_ready(preparation, problem):
    ctx = preparation
    receive(ctx, UUID(pay(ctx).json()["transfer_ids"][0]))
    assert transition(ctx, "preparation", "PAGADO").status_code == 200
    with ctx.factory.begin() as db:
        reserve = db.scalar(select(ReservaPedido).where(ReservaPedido.pedido_id == ctx.order_id, ReservaPedido.activa.is_(True)))
        lot = db.get(LoteInventario, reserve.lote_id)
        if problem == "missing":
            reserve.activa = False
        elif problem == "expired":
            lot.fecha_vencimiento = datetime.now(timezone.utc).date()
        elif problem == "inactive":
            lot.activo = False
        else:
            lot.cantidad = 0
    assert transition(ctx, "ready", "EN_PREPARACION").status_code == 409
    with ctx.factory() as db:
        assert db.get(PedidoOnline, ctx.order_id).estado == "EN_PREPARACION"


def test_session_permission_and_origin(preparation):
    ctx = preparation
    assert ctx.client.post(f"/api/orders/{ctx.order_id}/preparation", json={"expected_state": "PAGADO"},
                           headers={"origin": "https://untrusted.invalid"}).status_code == 403
    with ctx.factory.begin() as db:
        user = db.get(UsuarioInterno, ctx.ids["admin"])
        user.roles = []
    assert ctx.client.get("/api/orders").status_code == 403
    assert transition(ctx, "preparation", "PAGADO").status_code == 403
    ctx.client.cookies.clear()
    assert ctx.client.get("/api/orders").status_code == 401


def test_branch_scope_and_read_only(preparation):
    ctx = preparation
    pay(ctx)
    with ctx.factory.begin() as db:
        role = Rol(codigo="PEDIDOS_QA_" + ctx.suffix, nombre="Consulta QA")
        role.permisos = list(db.scalars(select(Permiso).where(Permiso.codigo == "pedidos.consultar")))
        user = db.get(UsuarioInterno, ctx.ids["admin"])
        user.roles = [role]
        user.sucursal_id = ctx.ids["branch"]
    assert ctx.client.get(f"/api/orders/{ctx.order_id}").status_code == 403
    assert ctx.client.get("/api/orders").json()["orders"] == []
    assert ctx.client.get(f"/api/orders?branch_id={ctx.cart_ids['destination']}").status_code == 403
    assert ctx.client.get(f"/api/orders?branch_ids={ctx.ids['branch']}&branch_ids={ctx.cart_ids['destination']}").status_code == 403
    with ctx.factory.begin() as db:
        db.get(UsuarioInterno, ctx.ids["admin"]).sucursal_id = ctx.cart_ids["destination"]
    detail = ctx.client.get(f"/api/orders/{ctx.order_id}")
    assert detail.status_code == 200 and not detail.json()["actions"]
    assert transition(ctx, "preparation", "PAGADO").status_code == 403


def test_filters_and_validation(preparation):
    ctx = preparation
    pay(ctx)
    response = ctx.client.get("/api/orders?state=PAGADO&limit=1")
    assert response.status_code == 200 and len(response.json()["orders"]) == 1
    assert ctx.client.get("/api/orders?state=INVENTADO").status_code == 422
    assert ctx.client.get("/api/orders?page=0").status_code == 422
    assert ctx.client.post(f"/api/orders/{ctx.order_id}/preparation", json={}).status_code == 422


def test_local_order_can_be_prepared_by_own_branch_staff(preparation):
    from test_orders import order_payload
    ctx = preparation
    pay(ctx, "failed")
    payload = order_payload(ctx, quantity=1)
    assert ctx.client.post("/api/customers/orders", json=payload).status_code == 201
    ctx.order_id = UUID(payload["request_id"])
    assert pay(ctx).json()["transfer_ids"] == []
    with ctx.factory.begin() as db:
        role = Rol(codigo="PREPARADOR_" + ctx.suffix, nombre="Preparador QA")
        role.permisos = list(db.scalars(select(Permiso).where(Permiso.codigo.in_(("pedidos.consultar", "pedidos.preparar")))))
        user = db.get(UsuarioInterno, ctx.ids["admin"])
        user.roles = [role]
        user.sucursal_id = ctx.cart_ids["destination"]
    assert transition(ctx, "preparation", "PAGADO").status_code == 200
    assert transition(ctx, "ready", "EN_PREPARACION").status_code == 200


def test_multiple_states_sorting_and_pagination(preparation):
    from test_orders import order_payload
    ctx = preparation
    pay(ctx, "failed")
    payload = order_payload(ctx, quantity=1)
    assert ctx.client.post("/api/customers/orders", json=payload).status_code == 201
    ctx.order_id = UUID(payload["request_id"])
    assert pay(ctx).status_code == 200
    base = f"/api/orders?branch_id={ctx.cart_ids['destination']}&states=PAGADO&states=CANCELADO&limit=1"
    response = ctx.client.get(base + "&sort=state_asc")
    assert response.status_code == 200
    assert response.json()["total"] == 2
    assert response.json()["orders"][0]["status"] == "PAGADO"
    assert ctx.client.get(base + "&sort=state_asc&page=2").json()["orders"][0]["status"] == "CANCELADO"
    assert ctx.client.get(base + "&sort=state_desc").json()["orders"][0]["status"] == "CANCELADO"
    assert ctx.client.get(base + "&states=INVENTADO").status_code == 422
    assert ctx.client.get(base + "&sort=INVALIDO").status_code == 422
    assert ctx.client.get(base + "&state=PAGADO").status_code == 422
    # El parámetro anterior sigue funcionando para consumidores existentes.
    assert ctx.client.get(f"/api/orders?branch_id={ctx.cart_ids['destination']}&state=PAGADO").json()["total"] == 1


def test_branch_multiselect_and_global_sort(preparation):
    from test_orders import order_payload

    from app.models import Sucursal
    ctx = preparation
    pay(ctx, "failed")
    with ctx.factory.begin() as db:
        db.get(Sucursal, ctx.ids['branch']).nombre = 'AAA Origen QA'
        db.get(Sucursal, ctx.cart_ids['destination']).nombre = 'ZZZ Destino QA'
    payload = order_payload(ctx, quantity=1)
    payload['pickup_branch_id'] = str(ctx.ids['branch'])
    assert ctx.client.post('/api/customers/orders', json=payload).status_code == 201
    base = f"/api/orders?branch_ids={ctx.ids['branch']}&branch_ids={ctx.cart_ids['destination']}&limit=1"
    response = ctx.client.get(base + '&sort=branch_asc')
    assert response.status_code == 200
    assert response.json()['total'] == 2
    assert response.json()['orders'][0]['pickup_branch']['id'] == str(ctx.ids['branch'])
    assert ctx.client.get(base + '&sort=branch_desc').json()['orders'][0]['pickup_branch']['id'] == str(ctx.cart_ids['destination'])
    assert ctx.client.get(base + '&sort=branch_asc&page=2').json()['orders'][0]['pickup_branch']['id'] == str(ctx.cart_ids['destination'])
    assert ctx.client.get(base + '&states=CANCELADO').json()['total'] == 1
    assert ctx.client.get(base + f"&branch_id={ctx.ids['branch']}").status_code == 422
    assert ctx.client.get('/api/orders?branch_ids=invalid').status_code == 422
