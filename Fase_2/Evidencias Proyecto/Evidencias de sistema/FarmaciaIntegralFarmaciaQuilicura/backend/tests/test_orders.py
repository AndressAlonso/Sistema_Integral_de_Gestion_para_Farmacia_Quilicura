# ruff: noqa: F811
from datetime import datetime, timezone
from uuid import UUID, uuid4

import pytest
from sqlalchemy import func, select
from test_e6_cart import cart, snapshot, validate  # noqa: F401

from app.customers.models import Cliente
from app.models import InventarioSucursal, LoteInventario
from app.orders.models import PedidoOnline, ReservaPedido
from app.pos.service import PosService


def order_payload(ctx, quantity=5):
    return {
        "request_id": str(uuid4()),
        "request_token": uuid4().hex + uuid4().hex,
        "pickup_branch_id": str(ctx.cart_ids["destination"]),
        "items": [{"product_id": str(ctx.cart_ids["product"]), "quantity": quantity}],
        "guest": {"name": "Invitado QA", "email": "guest@example.com"},
        "expected_total": str(quantity * 12.5),
        "confirmed": True,
    }


def test_order_reserves_fefo_without_physical_exit_or_customer_creation(cart):
    with cart.factory() as db:
        customers = db.scalar(select(func.count()).select_from(Cliente))
    cart.client._transport.raise_server_exceptions = True
    data = order_payload(cart)
    response = cart.client.post("/api/customers/orders", json=data)
    assert response.status_code == 201, response.text
    assert (
        response.json()["status"] == "PENDIENTE_PAGO"
        and response.json()["total"] == "62.50"
    )
    assert response.json()["pickup_branch"]["id"] == data["pickup_branch_id"]
    with cart.factory() as db:
        row = db.get(PedidoOnline, UUID(data["request_id"]))
        assert (
            row.cliente_id is None
            and row.nombre == "Invitado QA"
            and row.correo == "guest@example.com"
        )
        assert db.scalar(select(func.count()).select_from(Cliente)) == customers
        origin = db.get(InventarioSucursal, cart.cart_ids["origin_inventory"])
        destination = db.get(InventarioSucursal, cart.cart_ids["destination_inventory"])
        assert (origin.stock_fisico, origin.stock_reservado) == (14, 4)
        assert (destination.stock_fisico, destination.stock_reservado) == (3, 3)
        assert db.get(LoteInventario, cart.cart_ids["fresh"]).cantidad == 10
        reservations = list(
            db.scalars(select(ReservaPedido).where(ReservaPedido.pedido_id == row.id))
        )
        assert sum(r.cantidad for r in reservations) == 5
        assert cart.cart_ids["expired"] not in {r.lote_id for r in reservations}
        assert (
            PosService.availability(
                db, cart.cart_ids["product"], cart.cart_ids["destination"]
            )[2]
            == 0
        )
    assert validate(cart, quantity=7).json()["valid"] is False


def test_same_request_and_capability_are_idempotent(cart):
    data = order_payload(cart)
    assert cart.client.post("/api/customers/orders", json=data).status_code == 201
    before = snapshot(cart)
    assert cart.client.post("/api/customers/orders", json=data).status_code == 200
    assert snapshot(cart) == before
    assert (
        cart.client.post(
            "/api/customers/orders", json=dict(data, request_token="b" * 64)
        ).status_code
        == 409
    )
    assert (
        cart.client.post(
            "/api/customers/orders/" + data["request_id"] + "/status",
            json={"request_token": data["request_token"]},
        ).status_code
        == 200
    )
    assert (
        cart.client.post(
            "/api/customers/orders/" + data["request_id"] + "/status",
            json={"request_token": "b" * 64},
        ).status_code
        == 404
    )


@pytest.mark.parametrize(
    "change",
    [
        "price",
        "stock",
        "prescription",
        "branch",
        "confirmation",
        "guest",
        "negative",
        "duplicate",
    ],
)
def test_invalid_order_has_no_partial_reservation(cart, change):
    data = order_payload(cart)
    if change == "price":
        data["expected_total"] = "1"
    if change == "stock":
        data["items"][0]["quantity"] = 12
        data["expected_total"] = "150"
    if change == "prescription":
        data["items"][0]["product_id"] = str(cart.cart_ids["prescription"])
    if change == "branch":
        data["pickup_branch_id"] = str(cart.cart_ids["closed"])
    if change == "confirmation":
        data["confirmed"] = False
    if change == "guest":
        data["guest"]["email"] = "invalid"
    if change == "negative":
        data["items"][0]["quantity"] = -1
    if change == "duplicate":
        data["items"].append(dict(data["items"][0]))
    before = snapshot(cart)
    assert cart.client.post("/api/customers/orders", json=data).status_code in (
        409,
        422,
    )
    assert snapshot(cart) == before
    with cart.factory() as db:
        assert db.get(PedidoOnline, UUID(data["request_id"])) is None


def test_registered_order_is_owned_and_guest_email_never_links_account(cart):
    body = {
        "name": "Cliente QA",
        "email": cart.suffix + "@example.com",
        "password": "Password-Only-QA-123!",
    }
    assert cart.client.post("/api/customers/register", json=body).status_code == 201
    assert (
        cart.client.post(
            "/api/customers/login",
            json={"email": body["email"], "password": body["password"]},
        ).status_code
        == 200
    )
    data = order_payload(cart, quantity=1)
    data["guest"] = None
    response = cart.client.post("/api/customers/orders", json=data)
    assert response.status_code == 201, response.text
    history = cart.client.get("/api/customers/orders")
    assert history.status_code == 200 and len(history.json()["orders"]) == 1
    assert history.json()["orders"][0]["id"] == data["request_id"]
    cart.client.post("/api/customers/logout")
    assert cart.client.get("/api/customers/orders").status_code == 401
    guest = order_payload(cart, quantity=1)
    guest["guest"]["email"] = body["email"]
    assert cart.client.post("/api/customers/orders", json=guest).status_code == 201
    cart.client.post(
        "/api/customers/login",
        json={"email": body["email"], "password": body["password"]},
    )
    assert len(cart.client.get("/api/customers/orders").json()["orders"]) == 1


def test_origin_is_checked_before_reserving(cart):
    before = snapshot(cart)
    assert (
        cart.client.post(
            "/api/customers/orders",
            json=order_payload(cart),
            headers={"Origin": "https://invalid.example"},
        ).status_code
        == 403
    )
    assert snapshot(cart) == before


def test_history_cursor_private_ownership_and_branch_guard(cart):
    from app.branches.repository import BranchPendingOrders, PostgresBranchRepository

    body = {
        "name": "Cliente QA",
        "email": cart.suffix + "@example.com",
        "password": "Password-Only-QA-123!",
    }
    cart.client.post("/api/customers/register", json=body)
    cart.client.post(
        "/api/customers/login",
        json={"email": body["email"], "password": body["password"]},
    )
    identifiers = []
    for _ in range(2):
        data = order_payload(cart, quantity=1)
        data["guest"] = None
        assert cart.client.post("/api/customers/orders", json=data).status_code == 201
        identifiers.append(UUID(data["request_id"]))
    with cart.factory.begin() as db:
        point = datetime.now(timezone.utc)
        for identity in identifiers:
            row = db.get(PedidoOnline, identity)
            row.creado_en = point
    first = cart.client.get("/api/customers/orders?limit=1").json()
    second = cart.client.get(
        "/api/customers/orders", params={"limit": 1, "cursor": first["next_cursor"]}
    ).json()
    assert first["orders"][0]["id"] != second["orders"][0]["id"]
    assert second["next_cursor"] is None
    assert cart.client.get("/api/customers/orders?cursor=invalid").status_code == 422
    with pytest.raises(BranchPendingOrders):
        PostgresBranchRepository(cart.factory).deactivate(cart.cart_ids["destination"])
    cart.client.post("/api/customers/logout")
    other = dict(body, email="other-" + body["email"])
    cart.client.post("/api/customers/register", json=other)
    cart.client.post(
        "/api/customers/login",
        json={"email": other["email"], "password": other["password"]},
    )
    assert cart.client.get("/api/customers/orders").json()["orders"] == []
