"""E7-H3: pedidos y transferencias sobre PostgreSQL con rollback."""
from types import SimpleNamespace
from uuid import UUID

import pytest
from sqlalchemy import func, select
from test_auth import login
from test_e6_cart import cart  # noqa: F401
from test_orders import order_payload

from app.models import (
    EventoAuditoria,
    InventarioSucursal,
    LoteInventario,
    Rol,
    Transferencia,
    UsuarioInterno,
)
from app.orders.models import PedidoOnline, ReservaPedido
from app.transfers.repository import TransferRepository
from app.transfers.schemas import ReceiveTransfer
from app.transfers.service import TransferError, TransferService

BASE = "/api/orders/development"


@pytest.fixture
def online(cart):  # noqa: F811
    cart.app.state.settings.app_environment = "development"
    cart.app.state.settings.order_payment_simulation = True
    with cart.factory.begin() as db:
        role = db.scalar(select(Rol).where(Rol.codigo == "ADMINISTRADOR"))
        if role is None:
            role = Rol(codigo="ADMINISTRADOR", nombre="Administrador")
            db.add(role)
        user = db.get(UsuarioInterno, cart.ids["admin"])
        if role not in user.roles:
            user.roles.append(role)
    data = order_payload(cart)
    response = cart.client.post("/api/customers/orders", json=data)
    assert response.status_code == 201, response.text
    assert login(cart).status_code == 200
    cart.order_id = UUID(data["request_id"])
    cart.actor = SimpleNamespace(id=cart.ids["admin"], branch_id=cart.ids["branch"],
                                 is_active=True, roles=["ADMINISTRADOR"],
                                 permissions=["transferencias." + a for a in
                                              ("consultar", "solicitar", "autorizar", "despachar", "recibir")])
    return cart


def pay(ctx, outcome="accepted"):
    return ctx.client.post(f"{BASE}/orders/{ctx.order_id}/payment",
                           json={"outcome": outcome, "confirmed": True})


def test_paid_order_transfer_complete_and_idempotent(online):
    ctx = online
    before = None
    with ctx.factory() as db:
        before = db.get(InventarioSucursal, ctx.cart_ids["origin_inventory"]).stock_reservado
    response = pay(ctx)
    assert response.status_code == 200, response.text
    assert len(response.json()["transfer_ids"]) == 1
    transfer_id = UUID(response.json()["transfer_ids"][0])
    again = pay(ctx)
    assert again.status_code == 200 and not again.json()["changed"]
    assert again.json()["transfer_ids"] == response.json()["transfer_ids"]
    assert pay(ctx, "failed").status_code == 409
    repo = TransferRepository(ctx.factory)
    service = TransferService(repo)
    view = service.get(ctx.actor, transfer_id)
    assert view["order_id"] == ctx.order_id and view["requested_by"] == "Sistema"
    assert view["state"] == "AUTORIZADA" and view["actions"] == ["dispatch"]
    with ctx.factory() as db:
        assert db.get(InventarioSucursal, ctx.cart_ids["origin_inventory"]).stock_reservado == before
        # La fixture tiene dos reservas agregadas sin lote; este pedido asigna dos al lote.
        assert repo.reserved_lots(db, ctx.cart_ids["origin_inventory"])[ctx.cart_ids["fresh"]] == 2
        assert db.scalar(select(func.count()).select_from(EventoAuditoria).where(
            EventoAuditoria.accion == "E7-H3_PAGO_SIMULADO",
            EventoAuditoria.referencia_historica == f"Pedido {ctx.order_id}")) == 1
    with pytest.raises(TransferError) as exc:
        service.change(ctx.actor, transfer_id, "reject", SimpleNamespace(reason="No"))
    assert exc.value.status == 409
    service.change(ctx.actor, transfer_id, "dispatch")
    service.change(ctx.actor, transfer_id, "dispatch")
    with ctx.factory() as db:
        origin = db.get(InventarioSucursal, ctx.cart_ids["origin_inventory"])
        destination = db.get(InventarioSucursal, ctx.cart_ids["destination_inventory"])
        assert (origin.stock_fisico, origin.stock_reservado) == (12, 2)
        assert (destination.stock_fisico, destination.stock_reservado) == (3, 3)
    bad = ReceiveTransfer(items=[{"product_id": ctx.cart_ids["product"], "quantity": 1}])
    with pytest.raises(TransferError):
        service.change(ctx.actor, transfer_id, "receive", bad)
    received = ReceiveTransfer(items=[{"product_id": ctx.cart_ids["product"], "quantity": 2}])
    service.change(ctx.actor, transfer_id, "receive", received)
    service.change(ctx.actor, transfer_id, "receive", received)
    with ctx.factory() as db:
        destination = db.get(InventarioSucursal, ctx.cart_ids["destination_inventory"])
        assert (destination.stock_fisico, destination.stock_reservado, destination.stock_disponible) == (5, 5, 0)
        rows = list(db.scalars(select(ReservaPedido).where(
            ReservaPedido.pedido_id == ctx.order_id, ReservaPedido.activa.is_(True))))
        assert sum(r.cantidad for r in rows) == 5
        for row in rows:
            lot = db.get(LoteInventario, row.lote_id)
            assert lot.inventario_sucursal_id == destination.id
        assert db.get(Transferencia, transfer_id).estado == "RECIBIDA"


def test_failed_payment_releases_only_its_reservations(online):
    assert pay(online, "failed").status_code == 200
    assert pay(online, "failed").json()["changed"] is False
    assert pay(online).status_code == 409
    with online.factory() as db:
        assert db.get(PedidoOnline, online.order_id).estado == "CANCELADO"
        assert not list(db.scalars(select(Transferencia).where(Transferencia.pedido_id == online.order_id)))
        assert not list(db.scalars(select(ReservaPedido).where(
            ReservaPedido.pedido_id == online.order_id, ReservaPedido.activa.is_(True))))
        assert db.get(InventarioSucursal, online.cart_ids["origin_inventory"]).stock_reservado == 2
        assert db.get(InventarioSucursal, online.cart_ids["destination_inventory"]).stock_reservado == 0


def test_no_transfer_before_payment_and_local_order_needs_none(online):
    with online.factory() as db:
        assert not list(db.scalars(select(Transferencia).where(Transferencia.pedido_id == online.order_id)))
    pay(online, "failed")
    data = order_payload(online, quantity=1)
    response = online.client.post("/api/customers/orders", json=data)
    assert response.status_code == 201
    online.order_id = UUID(data["request_id"])
    assert pay(online).json()["transfer_ids"] == []


@pytest.mark.parametrize("mode", ["production", "disabled", "no_session", "non_admin", "origin"])
def test_simulator_security(online, mode):
    if mode == "production":
        online.app.state.settings.app_environment = "production"
    elif mode == "disabled":
        online.app.state.settings.order_payment_simulation = False
    elif mode == "no_session":
        online.client.cookies.clear()
    elif mode == "non_admin":
        online.client.cookies.clear()
        assert login(online, "operator").status_code == 200
    headers = {"Origin": "https://evil.example"} if mode == "origin" else {}
    result = online.client.post(f"{BASE}/orders/{online.order_id}/payment",
                               json={"outcome": "accepted", "confirmed": True}, headers=headers)
    assert result.status_code == (404 if mode in ("production", "disabled") else 401 if mode == "no_session" else 403)
    with online.factory() as db:
        assert db.get(PedidoOnline, online.order_id).estado == "PENDIENTE_PAGO"


def test_expired_reserved_lot_does_not_leave_partial_payment(online):
    from datetime import datetime, timezone
    with online.factory.begin() as db:
        db.get(LoteInventario, online.cart_ids["fresh"]).fecha_vencimiento = datetime.now(timezone.utc).date()
    assert pay(online).status_code == 409
    with online.factory() as db:
        assert db.get(PedidoOnline, online.order_id).estado == "PENDIENTE_PAGO"
        assert not list(db.scalars(select(Transferencia).where(Transferencia.pedido_id == online.order_id)))


def test_transfer_scope_is_enforced(online):
    transfer_id = UUID(pay(online).json()["transfer_ids"][0])
    actor = SimpleNamespace(**vars(online.actor))
    actor.roles = ["ENCARGADO_INVENTARIO"]
    actor.branch_id = online.cart_ids["closed"]
    with pytest.raises(TransferError) as exc:
        TransferService(TransferRepository(online.factory)).get(actor, transfer_id)
    assert exc.value.status == 403

def test_multiple_origins_merge_same_lot_in_destination(online):
    from uuid import uuid4

    from app.models import Sucursal
    ctx = online
    assert pay(ctx, "failed").status_code == 200
    extra_branch = uuid4()
    with ctx.factory.begin() as db:
        db.add(Sucursal(id=extra_branch, codigo="OT-" + ctx.suffix[:20],
                        nombre="Otra origen", direccion_local="Prueba", activa=True))
        db.flush()
        inv = InventarioSucursal(producto_id=ctx.cart_ids["product"], sucursal_id=extra_branch,
                                 stock_fisico=3, stock_reservado=0, stock_minimo=0)
        db.add(inv)
        db.flush()
        source_lot = db.get(LoteInventario, ctx.cart_ids["fresh"])
        source_lot.cantidad = 3
        db.get(InventarioSucursal, ctx.cart_ids["origin_inventory"]).stock_fisico = 7
        db.add(LoteInventario(inventario_sucursal_id=inv.id, numero_lote="fresh",
                             fecha_vencimiento=source_lot.fecha_vencimiento, cantidad=3, activo=True))
        local = db.scalar(select(LoteInventario).where(
            LoteInventario.inventario_sucursal_id == ctx.cart_ids["destination_inventory"]))
        local.numero_lote = "fresh"
    data = order_payload(ctx, quantity=7)
    assert ctx.client.post("/api/customers/orders", json=data).status_code == 201
    ctx.order_id = UUID(data["request_id"])
    result = pay(ctx)
    assert result.status_code == 200, result.text
    assert len(result.json()["transfer_ids"]) == 2
    service = TransferService(TransferRepository(ctx.factory))
    for identity in result.json()["transfer_ids"]:
        identity = UUID(identity)
        view = service.get(ctx.actor, identity)
        service.change(ctx.actor, identity, "dispatch")
        service.change(ctx.actor, identity, "receive", ReceiveTransfer(
            items=[{"product_id": i["product_id"], "quantity": i["quantity"]} for i in view["items"]]))
    with ctx.factory() as db:
        dest = db.get(InventarioSucursal, ctx.cart_ids["destination_inventory"])
        assert (dest.stock_fisico, dest.stock_reservado, dest.stock_disponible) == (7, 7, 0)
        reservations = list(db.scalars(select(ReservaPedido).where(
            ReservaPedido.pedido_id == ctx.order_id, ReservaPedido.activa.is_(True))))
        assert len(reservations) == 1 and reservations[0].cantidad == 7


def test_paid_local_order_prevents_branch_deactivation(online):
    from app.branches.repository import BranchPendingOrders, PostgresBranchRepository
    assert pay(online, "failed").status_code == 200
    data = order_payload(online, quantity=1)
    assert online.client.post("/api/customers/orders", json=data).status_code == 201
    online.order_id = UUID(data["request_id"])
    assert pay(online).status_code == 200
    with pytest.raises(BranchPendingOrders):
        PostgresBranchRepository(online.factory).deactivate(online.cart_ids["destination"])


def test_order_manager_can_follow_but_not_operate(online):
    from app.role_catalog import reconcile_e7_permissions
    with online.factory.begin() as db:
        role = db.scalar(select(Rol).where(Rol.codigo == "ENCARGADO_PEDIDOS"))
        if role is None:
            role = Rol(codigo="ENCARGADO_PEDIDOS", nombre="Pedidos")
            db.add(role)
        from app.models import Permiso
        permission = db.scalar(select(Permiso).where(Permiso.codigo == "transferencias.consultar"))
        if permission is None:
            db.add(Permiso(codigo="transferencias.consultar", descripcion="Consulta"))
        db.flush()
        reconcile_e7_permissions(db)
        reconcile_e7_permissions(db)
        codes = [p.codigo for p in role.permisos]
        assert codes.count("transferencias.consultar") == 1
    transfer_id = UUID(pay(online).json()["transfer_ids"][0])
    actor = SimpleNamespace(id=online.ids["operator"], branch_id=online.cart_ids["destination"],
                            is_active=True, roles=["ENCARGADO_PEDIDOS"], permissions=["transferencias.consultar"])
    service = TransferService(TransferRepository(online.factory))
    assert service.get(actor, transfer_id)["actions"] == []
    with pytest.raises(TransferError):
        service.change(actor, transfer_id, "dispatch")


