"""E6-H4: PostgreSQL real, fixtures DML con rollback y validaciones sin escrituras."""
from datetime import timedelta
from decimal import Decimal
from uuid import uuid4

import pytest
from app.models import (
    Categoria,
    InventarioSucursal,
    LoteInventario,
    MovimientoInventario,
    Producto,
    Sucursal,
    Transferencia,
    TransferenciaDetalle,
    TransferenciaLote,
)
from sqlalchemy import func, select


@pytest.fixture
def cart(setup):
    ctx = setup
    ctx.cart_ids = {key: uuid4() for key in ("category", "product", "prescription", "inactive", "hidden", "destination", "closed", "origin_inventory", "destination_inventory", "fresh", "expired")}
    ids = ctx.cart_ids
    with ctx.factory.begin() as db:
        ctx.cart_today = db.scalar(select(func.current_date()))
        db.add(Categoria(id=ids["category"], nombre="Carrito " + ctx.suffix))
        for key, active in (("destination", True), ("closed", False)):
            db.add(Sucursal(id=ids[key], codigo=key[:3] + ctx.suffix[:20], nombre=key, direccion_local="Temporal", activa=active))
        db.flush()
        for key in ("product", "prescription", "inactive", "hidden"):
            db.add(Producto(id=ids[key], sku=key + ctx.suffix, nombre=key, descripcion="Temporal", categoria_id=ids["category"], precio_actual=Decimal("12.50"), activo=key != "inactive", publicado_online=key != "hidden", requiere_receta=key == "prescription"))
        db.flush()
        db.add_all([
            InventarioSucursal(id=ids["origin_inventory"], producto_id=ids["product"], sucursal_id=ctx.ids["branch"], stock_fisico=14, stock_reservado=2),
            InventarioSucursal(id=ids["destination_inventory"], producto_id=ids["product"], sucursal_id=ids["destination"], stock_fisico=3, stock_reservado=0),
        ])
        db.flush()
        db.add_all([
            LoteInventario(id=ids["fresh"], inventario_sucursal_id=ids["origin_inventory"], numero_lote="fresh", cantidad=10, fecha_vencimiento=ctx.cart_today + timedelta(days=30), activo=True),
            LoteInventario(id=ids["expired"], inventario_sucursal_id=ids["origin_inventory"], numero_lote="expired", cantidad=4, fecha_vencimiento=ctx.cart_today, activo=True),
            LoteInventario(inventario_sucursal_id=ids["destination_inventory"], numero_lote="destination", cantidad=3, fecha_vencimiento=ctx.cart_today + timedelta(days=30), activo=True),
        ])
    return ctx


def validate(ctx, quantity=5, product="product", branch="destination"):
    return ctx.client.post("/api/ecommerce/cart/validate", json={
        "items": [{"product_id": str(ctx.cart_ids[product]), "quantity": quantity}],
        "pickup_branch_id": str(ctx.cart_ids[branch]) if branch else None,
    })


def snapshot(ctx):
    with ctx.factory() as db:
        return (
            list(db.execute(select(InventarioSucursal.id, InventarioSucursal.stock_fisico, InventarioSucursal.stock_reservado).order_by(InventarioSucursal.id)).all()),
            list(db.execute(select(LoteInventario.id, LoteInventario.cantidad).order_by(LoteInventario.id)).all()),
            db.scalar(select(func.count()).select_from(MovimientoInventario)),
            db.scalar(select(func.count()).select_from(Transferencia)),
        )


def test_prices_transfer_and_no_writes(cart):
    before = snapshot(cart)
    response = validate(cart)
    assert response.status_code == 200
    data = response.json()
    assert data["valid"] and data["total"] == "62.50"
    line = data["items"][0]
    assert line["global_available"] == 11 and line["local_available"] == 3
    assert line["requires_transfer"]
    assert validate(cart, quantity=2).json()["items"][0]["requires_transfer"] is False
    assert snapshot(cart) == before
    with cart.factory.begin() as db:
        db.get(Producto, cart.cart_ids["product"]).precio_actual = Decimal("13.25")
    assert validate(cart).json()["total"] == "66.25"


@pytest.mark.parametrize("product", ["prescription", "inactive", "hidden"])
def test_restricted_products(cart, product):
    data = validate(cart, product=product).json()
    assert not data["valid"] and data["total"] is None
    assert not data["items"][0]["valid"] and data["items"][0]["issues"]


def test_missing_product_and_inactive_branch(cart):
    cart.cart_ids["missing"] = uuid4()
    assert not validate(cart, product="missing").json()["items"][0]["valid"]
    data = validate(cart, branch="closed").json()
    assert not data["valid"] and data["pickup_branch"] is None and len(data["items"]) == 1
    with cart.factory.begin() as db:
        db.get(Sucursal, cart.cart_ids["destination"]).activa = False
    assert validate(cart).json()["pickup_branch"] is None


@pytest.mark.parametrize("quantity", [0, -1, 100, 1.5, True, "2"])
def test_invalid_quantities(cart, quantity):
    assert validate(cart, quantity=quantity).status_code == 422


def test_limits_and_duplicate_ids(cart):
    row = {"product_id": str(cart.cart_ids["product"]), "quantity": 1}
    assert cart.client.post("/api/ecommerce/cart/validate", json={"items": [row, row]}).status_code == 422
    rows = [{"product_id": str(uuid4()), "quantity": 1} for _ in range(51)]
    assert cart.client.post("/api/ecommerce/cart/validate", json={"items": rows}).status_code == 422
    assert cart.client.post("/api/ecommerce/cart/validate", json={"items": rows[:50]}).status_code == 200
    assert validate(cart, quantity=99).status_code == 200


def test_insufficient_global_and_missing_branch(cart):
    data = validate(cart, quantity=12).json()
    assert not data["items"][0]["valid"] and data["total"] is None
    assert not data["items"][0]["requires_transfer"]
    data = validate(cart, branch=None).json()
    assert data["items"][0]["valid"] and not data["valid"] and data["total"] is None


@pytest.mark.parametrize("variant", ["physical", "missing_lot", "inactive_lot", "expired"])
def test_inventory_inconsistencies_and_expired_lots(cart, variant):
    with cart.factory.begin() as db:
        lot = db.get(LoteInventario, cart.cart_ids["fresh"])
        if variant == "physical":
            db.get(InventarioSucursal, cart.cart_ids["origin_inventory"]).stock_fisico += 1
        elif variant == "missing_lot":
            lot.cantidad -= 1
        elif variant == "inactive_lot":
            lot.activo = False
        else:
            lot.fecha_vencimiento = cart.cart_today - timedelta(days=1)
    data = validate(cart).json()
    assert not data["valid"] and data["total"] is None
    assert data["items"][0]["issues"]
    assert "SQL" not in str(data)


def test_assigned_reservations_and_transit(cart):
    ids = cart.cart_ids
    transfer_id, detail_id = uuid4(), uuid4()
    with cart.factory.begin() as db:
        db.add(Transferencia(id=transfer_id, solicitud_hash="0" * 64, origen_id=cart.ids["branch"], destino_id=ids["destination"], estado="SOLICITADA", solicitante_id=cart.ids["admin"]))
        db.flush()
        db.add(TransferenciaDetalle(id=detail_id, transferencia_id=transfer_id, producto_id=ids["product"], cantidad=2))
        db.flush()
        db.add(TransferenciaLote(detalle_id=detail_id, lote_origen_id=ids["expired"], cantidad=2))
    # La reserva asignada al lote vencido no se descuenta una segunda vez del vigente.
    assert validate(cart).json()["items"][0]["global_available"] == 13
    with cart.factory.begin() as db:
        db.get(TransferenciaDetalle, detail_id).cantidad = 3
        allocation = db.scalar(select(TransferenciaLote).where(TransferenciaLote.detalle_id == detail_id))
        allocation.cantidad = 3
    assert not validate(cart).json()["items"][0]["valid"]
    with cart.factory.begin() as db:
        db.get(Transferencia, transfer_id).estado = "EN_TRANSITO"
        db.get(InventarioSucursal, ids["origin_inventory"]).stock_reservado = 0
    # No incorpora el lote en tránsito a destino: allí siguen existiendo solo tres unidades.
    line = validate(cart).json()["items"][0]
    assert line["local_available"] == 3
