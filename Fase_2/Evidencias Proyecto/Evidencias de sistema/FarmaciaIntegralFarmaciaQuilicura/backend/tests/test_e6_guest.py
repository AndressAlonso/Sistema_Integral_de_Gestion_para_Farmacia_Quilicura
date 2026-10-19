"""E6-H3: validación sin escrituras con PostgreSQL y rollback."""
from decimal import Decimal
from secrets import token_urlsafe
from uuid import uuid4

import pytest
from app.customers.models import Cliente
from app.models import Base, Producto, Sucursal
from sqlalchemy import func, select
from test_e6_cart import (
    cart as cart,  # noqa: PLC0414 -- registrar fixture PostgreSQL compartida
)
from test_e6_cart import snapshot


def payload(ctx):
    return {
        "guest": {"name": " Visitante temporal ", "email": " VISITANTE@EXAMPLE.COM "},
        "cart": {"items": [{"product_id": str(ctx.cart_ids["product"]), "quantity": 5}],
                 "pickup_branch_id": str(ctx.cart_ids["destination"])},
    }


def row_counts(ctx):
    with ctx.factory() as db:
        return {table.name: db.scalar(select(func.count()).select_from(table)) for table in Base.metadata.sorted_tables}


def test_review_normalizes_and_does_not_write(cart):
    counts, stock = row_counts(cart), snapshot(cart)
    response = cart.client.post("/api/ecommerce/guest/validate", json=payload(cart))
    assert response.status_code == 200
    data = response.json()
    assert data["guest"] == {"name": "Visitante temporal", "email": "visitante@example.com"}
    assert data["cart"]["valid"] and data["cart"]["total"] == "62.50"
    assert data["cart"]["items"][0]["requires_transfer"]
    assert "set-cookie" not in response.headers
    assert counts == row_counts(cart) and stock == snapshot(cart)
    assert response.headers["cache-control"] == "no-store"


def test_existing_email_never_looks_up_or_creates_customer(cart, password_hash, monkeypatch):
    with cart.factory.begin() as db:
        db.add(Cliente(nombre="Temporal", correo="visitante@example.com", password_hash=password_hash))
    def forbidden(*args, **kwargs):
        raise AssertionError("El endpoint no debe consultar ni crear clientes")
    monkeypatch.setattr(cart.app.state.customers, "by_email", forbidden)
    monkeypatch.setattr(cart.app.state.customers, "by_id", forbidden)
    monkeypatch.setattr(cart.app.state.customers, "create", forbidden)
    before = row_counts(cart)
    response = cart.client.post("/api/ecommerce/guest/validate", json=payload(cart))
    assert response.status_code == 200 and response.json()["cart"]["valid"]
    assert row_counts(cart) == before


@pytest.mark.parametrize("field,value", [("name", "   "), ("name", "x" * 151), ("email", "invalid"), ("email", "")])
def test_invalid_guest_safe(cart, field, value):
    body = payload(cart)
    body["guest"][field] = value
    response = cart.client.post("/api/ecommerce/guest/validate", json=body)
    assert response.status_code == 422
    assert response.json() == {"detail": "Revisa el nombre, el correo, los productos y la sucursal de retiro."}


@pytest.mark.parametrize("where,field", [("guest", "password"), ("guest", "phone"), ("guest", "address"), ("root", "customer_id"), ("cart", "total"), ("item", "price")])
def test_extra_fields_rejected(cart, where, field):
    body = payload(cart)
    target = body if where == "root" else body["cart"]["items"][0] if where == "item" else body[where]
    value = token_urlsafe(24)
    target[field] = value
    response = cart.client.post("/api/ecommerce/guest/validate", json=body)
    assert response.status_code == 422 and value not in response.text


@pytest.mark.parametrize("variant", ["empty", "prescription", "hidden", "inactive", "quantity", "global", "branch", "missing_branch"])
def test_cart_revalidation(cart, variant):
    body = payload(cart)
    if variant == "empty":
        body["cart"]["items"] = []
    elif variant in ("prescription", "hidden", "inactive"):
        body["cart"]["items"][0]["product_id"] = str(cart.cart_ids[variant])
    elif variant == "quantity":
        body["cart"]["items"][0]["quantity"] = 100
    elif variant == "global":
        body["cart"]["items"][0]["quantity"] = 12
    elif variant == "missing_branch":
        body["cart"]["pickup_branch_id"] = None
    else:
        with cart.factory.begin() as db:
            db.get(Sucursal, cart.cart_ids["destination"]).activa = False
    counts, stock = row_counts(cart), snapshot(cart)
    response = cart.client.post("/api/ecommerce/guest/validate", json=body)
    if variant in ("quantity", "missing_branch"):
        assert response.status_code == 422
    else:
        assert response.status_code == 200
        assert not response.json()["cart"]["valid"] and response.json()["cart"]["total"] is None
    assert counts == row_counts(cart) and stock == snapshot(cart)


def test_price_is_reloaded_and_missing_product(cart):
    body = payload(cart)
    with cart.factory.begin() as db:
        db.get(Producto, cart.cart_ids["product"]).precio_actual = Decimal("20.25")
    assert cart.client.post("/api/ecommerce/guest/validate", json=body).json()["cart"]["total"] == "101.25"
    body["cart"]["items"][0]["product_id"] = str(uuid4())
    response = cart.client.post("/api/ecommerce/guest/validate", json=body)
    assert not response.json()["cart"]["valid"]


def test_origin_and_cookies_unchanged(cart):
    body = payload(cart)
    before = dict(cart.client.cookies)
    response = cart.client.post("/api/ecommerce/guest/validate", json=body, headers={"Origin": "https://untrusted.example"})
    assert response.status_code == 403
    assert dict(cart.client.cookies) == before and "set-cookie" not in response.headers
