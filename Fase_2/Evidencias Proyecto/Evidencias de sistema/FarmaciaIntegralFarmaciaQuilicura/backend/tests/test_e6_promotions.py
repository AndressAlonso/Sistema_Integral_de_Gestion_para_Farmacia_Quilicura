"""Promociones online: PostgreSQL real y rollback por fixture; sin ventas ni reservas."""
from datetime import timedelta
from decimal import Decimal
from uuid import uuid4

import pytest
from sqlalchemy import func, select
from test_e6_cart import cart, snapshot, validate  # noqa: F401

from app.models import Producto, Promocion


def promotion(ctx, kind="PERCENT", value="20", category=False, active=True, expired=False):
    key = uuid4()
    with ctx.factory.begin() as db:
        now = db.scalar(select(func.current_timestamp()))
        db.add(Promocion(id=key, nombre="Oferta QA", tipo=kind, valor=Decimal(value),
            inicia_en=now - timedelta(days=2), termina_en=now + timedelta(days=-1 if expired else 1),
            producto_id=None if category else ctx.cart_ids["product"],
            categoria_id=ctx.cart_ids["category"] if category else None, activo=active))
    return key


@pytest.mark.parametrize("category", [False, True])
@pytest.mark.parametrize("kind,value,expected", [("PERCENT", "20", "10.00"), ("FIXED_PRICE", "3.25", "3.25")])
def test_catalog_detail_and_cart_same_price(cart, category, kind, value, expected):  # noqa: F811
    before = snapshot(cart)
    key = promotion(cart, kind, value, category)
    product_id = str(cart.cart_ids["product"])
    detail = cart.client.get(f"/api/ecommerce/products/{product_id}")
    assert detail.status_code == 200, detail.text
    item = detail.json()
    rows = cart.client.get("/api/ecommerce/products").json()["products"]
    listing = next(row for row in rows if row["id"] == product_id)
    response = validate(cart, quantity=2)
    assert response.status_code == 200, response.text
    result = response.json()
    line = result["items"][0]
    assert listing["price"] == item["price"] == line["unit_price"] == expected
    assert item["base_price"] == line["base_unit_price"] == "12.50"
    assert Decimal(item["discount"]) == Decimal("12.50") - Decimal(expected)
    assert Decimal(line["unit_discount"]) == Decimal(item["discount"])
    assert item["promotion"]["code"] == line["promotion"]["code"] == str(key)
    assert item["promotion"]["kind"] == kind
    assert Decimal(result["total"]) == Decimal(line["subtotal"]) == Decimal(expected) * 2
    assert snapshot(cart) == before
    with cart.factory() as db:
        assert db.get(Producto, cart.cart_ids["product"]).precio_actual == Decimal("12.50")


def test_best_offer_and_revalidate_after_disabling(cart):  # noqa: F811
    promotion(cart)
    key = promotion(cart, "FIXED_PRICE", "3.25", category=True)
    assert validate(cart, quantity=2).json()["total"] == "6.50"
    with cart.factory.begin() as db:
        db.get(Promocion, key).activo = False
    assert validate(cart, quantity=2).json()["total"] == "20.00"


@pytest.mark.parametrize("active,expired,value", [(False, False, "3"), (True, True, "3"), (True, False, "20")])
def test_inactive_expired_or_higher_fixed_price_has_no_offer(cart, active, expired, value):  # noqa: F811
    promotion(cart, "FIXED_PRICE", value, active=active, expired=expired)
    item = cart.client.get(f"/api/ecommerce/products/{cart.cart_ids['product']}").json()
    line = validate(cart, quantity=2).json()["items"][0]
    assert item["price"] == line["unit_price"] == "12.50"
    assert item["promotion"] is None and line["promotion"] is None
    assert Decimal(item["discount"]) == 0


def test_prescription_still_visible_but_rejected_by_cart(cart):  # noqa: F811
    promotion(cart, category=True)
    item = cart.client.get(f"/api/ecommerce/products/{cart.cart_ids['prescription']}").json()
    assert item["price"] == "10.00" and item["requires_prescription"]
    assert item["online_purchase_allowed"] is False
    result = validate(cart, product="prescription").json()
    assert result["valid"] is False and result["items"][0]["unit_price"] is None
    assert any("receta" in issue for issue in result["items"][0]["issues"])
