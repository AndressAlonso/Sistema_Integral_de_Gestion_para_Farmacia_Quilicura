"""E5: datos ficticios con rollback; no utiliza ventas ni cuentas reales."""

from datetime import datetime, timedelta, timezone
from decimal import Decimal
from io import BytesIO
from uuid import UUID, uuid4

import pytest
from PIL import Image
from sqlalchemy import func, select
from test_auth import login
from test_transfers import transfer  # noqa: F401

from app.catalog.images import ProductImages
from app.models import (
    InventarioSucursal,
    LoteInventario,
    MovimientoInventario,
    Permiso,
    Producto,
    Rol,
    Venta,
)
from app.pos.pricing import Promotion, best_price


@pytest.mark.parametrize("payment", ["EFECTIVO", "DEBITO", "CREDITO"])
def test_current_payment_methods(pos, payment):
    cash = open_cash(pos)
    receipt = sell(pos, payment=payment)
    assert receipt["payment"] == payment
    summary = pos.client.get(f"/api/cash/{cash['id']}/summary").json()
    assert Decimal(summary["payments"][payment]) == Decimal(receipt["total"])


def test_new_transfer_payment_rejected_without_stock_change(pos):
    open_cash(pos)
    payload = sale_payload(pos, payment="TRANSFERENCIA")
    with pos.factory() as db:
        before = db.get(InventarioSucursal, pos.inventory_id).stock_fisico
    response = pos.client.post("/api/pos/sales", json=payload)
    assert response.status_code == 422
    with pos.factory() as db:
        assert db.get(Venta, UUID(payload["request_id"])) is None
        assert db.get(InventarioSucursal, pos.inventory_id).stock_fisico == before


def test_pos_image_reuses_catalog_without_edit_permission(pos, tmp_path):
    storage = ProductImages(tmp_path)
    image = BytesIO()
    Image.new("RGB", (32, 32), "green").save(image, format="PNG")
    key = storage.save(image.getvalue())
    pos.app.state.product_images = storage
    with pos.factory.begin() as db:
        db.get(Producto, pos.product_id).image_key = key
        role = db.get(Rol, pos.ids["operator_role"])
        role.permisos = [db.scalar(select(Permiso).where(Permiso.codigo == "pos.operar"))]
    assert login(pos, "operator").status_code == 200
    response = pos.client.get(f"/api/pos/products/{pos.product_id}/image")
    assert response.status_code == 200
    assert response.headers["content-type"] == "image/jpeg"
    assert response.content == storage.read(key)
    assert pos.client.post(f"/api/products/{pos.product_id}/image", content=image.getvalue()).status_code == 403


@pytest.mark.parametrize("variant", ["missing", "unknown", "inactive"])
def test_pos_image_unavailable(pos, variant):
    product_id = pos.product_id
    if variant == "unknown":
        product_id = uuid4()
    elif variant == "inactive":
        with pos.factory.begin() as db:
            db.get(Producto, product_id).activo = False
    assert pos.client.get(f"/api/pos/products/{product_id}/image").status_code == 404


def test_pos_image_requires_pos_permission(pos):
    assert login(pos, "operator").status_code == 200
    path = f"/api/pos/products/{pos.product_id}/image"
    assert pos.client.get(path).status_code == 403
    pos.client.cookies.clear()
    assert pos.client.get(path).status_code == 401


def test_demo_promotion_is_applied_by_api_and_preserved(pos):
    pos.settings.app_environment = "development"
    pos.settings.pos_demo_product_id = pos.product_id
    open_cash(pos)
    receipt = sell(pos, 2)
    assert receipt["total"] == "1600.00"
    assert receipt["discount"] == "400.00"
    assert receipt["items"][0]["promotion"]["code"] == "DEMO-E5-20"
    pos.settings.pos_demo_product_id = None
    stored = pos.client.get(f"/api/pos/sales/{receipt['id']}/receipt").json()
    assert stored["total"] == "1600.00"


def test_demo_rejected_in_production():
    from pydantic import ValidationError

    from app.config import Settings

    with pytest.raises(ValidationError):
        Settings(
            _env_file=None,
            jwt_secret_key="test-only-" * 5,
            app_environment="production",
            pos_demo_product_id=uuid4(),
        )


def test_sale_respects_transfer_reservations(pos):
    response = pos.client.post("/api/transfers", json=pos.payload)
    assert response.status_code == 201, response.text
    open_cash(pos)
    sell(pos, 12)
    with pos.factory() as db:
        inventory = db.get(InventarioSucursal, pos.inventory_id)
        assert inventory.stock_fisico == inventory.stock_reservado == 8
        assert db.get(LoteInventario, pos.early_id).cantidad == 5
        assert db.get(LoteInventario, pos.late_id).cantidad == 3


def test_full_void_and_no_second_return(pos):
    open_cash(pos)
    receipt = sell(pos, 2)
    data = reverse_payload(receipt, 2)
    data["kind"] = "ANULACION"
    url = f"/api/pos/sales/{receipt['id']}/reversals"
    assert pos.client.post(url, json=data).status_code == 200
    data["request_id"] = str(uuid4())
    assert pos.client.post(url, json=data).status_code == 409
    with pos.factory() as db:
        assert db.get(InventarioSucursal, pos.inventory_id).stock_fisico == 20


def test_return_expired_lot_cannot_restock(pos):
    open_cash(pos)
    receipt = sell(pos)
    with pos.factory.begin() as db:
        db.get(LoteInventario, pos.early_id).fecha_vencimiento = datetime.now(
            timezone.utc
        ).date() - timedelta(days=1)
    url = f"/api/pos/sales/{receipt['id']}/reversals"
    data = reverse_payload(receipt)
    assert pos.client.post(url, json=data).status_code == 409
    data["items"][0]["restock"] = False
    assert pos.client.post(url, json=data).status_code == 200


def test_permission_alone_does_not_allow_cashier_reversal(pos):
    open_cash(pos)
    receipt = sell(pos)
    with pos.factory.begin() as db:
        role = db.get(Rol, pos.ids["operator_role"])
        role.permisos = list(
            db.scalars(
                select(Permiso).where(
                    Permiso.codigo.in_(["pos.operar", "caja.operar", "ventas.reversar"])
                )
            )
        )
    assert login(pos, "operator").status_code == 200
    response = pos.client.post(
        f"/api/pos/sales/{receipt['id']}/reversals", json=reverse_payload(receipt)
    )
    assert response.status_code == 403


def test_branch_cannot_be_deactivated_with_open_cash(pos):
    open_cash(pos)
    from app.branches.repository import BranchOpenCash

    with pytest.raises(BranchOpenCash):
        pos.app.state.branches.deactivate(pos.ids["branch"])


def test_promotion_by_category_and_future_validity():
    now = datetime.now(timezone.utc)
    product, category = uuid4(), uuid4()
    active = Promotion(
        "category",
        "Categoría",
        "PERCENT",
        Decimal(10),
        now - timedelta(days=1),
        now + timedelta(days=1),
        category_id=category,
    )
    future = Promotion(
        "future",
        "Futura",
        "FIXED_PRICE",
        Decimal(1),
        now + timedelta(days=1),
        now + timedelta(days=2),
        product_id=product,
    )
    price, chosen = best_price(
        Decimal("999.99"), product, category, now, (active, future)
    )
    assert price == Decimal("899.99") and chosen["code"] == "category"


@pytest.fixture
def pos(transfer):  # noqa: F811 -- fixture compartido con los escenarios de stock E4
    ctx = transfer
    with ctx.factory.begin() as db:
        role = db.get(Rol, ctx.ids["admin_role"])
        for code in ("pos.operar", "caja.operar", "ventas.reversar"):
            permission = db.scalar(select(Permiso).where(Permiso.codigo == code))
            if permission is None:
                permission = Permiso(codigo=code, descripcion="Fixture E5")
                db.add(permission)
            if permission not in role.permisos:
                role.permisos.append(permission)
    return ctx


def open_cash(ctx, amount="0"):
    response = ctx.client.post(
        "/api/cash/open", json={"request_id": str(uuid4()), "initial_amount": amount}
    )
    assert response.status_code == 200, response.text
    return response.json()


def sale_payload(ctx, quantity=2, payment="EFECTIVO"):
    items = [{"product_id": str(ctx.product_id), "quantity": quantity}]
    response = ctx.client.post("/api/pos/quote", json={"items": items})
    assert response.status_code == 200, response.text
    return {
        "request_id": str(uuid4()),
        "items": items,
        "payment": payment,
        "quote_version": response.json()["version"],
    }


def sell(ctx, quantity=2, payment="EFECTIVO"):
    response = ctx.client.post(
        "/api/pos/sales", json=sale_payload(ctx, quantity, payment)
    )
    assert response.status_code == 200, response.text
    return response.json()


def reverse_payload(receipt, quantity=1, restock=True):
    item = receipt["items"][0]
    return {
        "request_id": str(uuid4()),
        "kind": "DEVOLUCION",
        "reason": "Devolución QA",
        "items": [
            {
                "product_id": item["product_id"],
                "sale_lot_id": item["lots"][0]["sale_lot_id"],
                "quantity": quantity,
                "restock": restock,
                "condition": "Envase revisado",
            }
        ],
    }


def test_cash_zero_and_duplicate(pos):
    cash = open_cash(pos)
    assert cash["initial_amount"] == "0"
    assert pos.client.get("/api/cash/current").json()["id"] == cash["id"]
    assert (
        pos.client.post(
            "/api/cash/open", json={"request_id": str(uuid4()), "initial_amount": "0"}
        ).status_code
        == 409
    )


def test_sale_without_cash(pos):
    assert pos.client.post("/api/pos/sales", json=sale_payload(pos)).status_code == 409


def test_search_available_and_zero(pos):
    response = pos.client.get("/api/pos/products", params={"q": str(pos.product_id)})
    assert response.status_code == 200, response.text
    assert response.json()["products"][0]["available"] == 20
    with pos.factory.begin() as db:
        db.get(InventarioSucursal, pos.inventory_id).stock_reservado = 20
    assert (
        pos.client.get("/api/pos/products", params={"q": str(pos.product_id)}).json()[
            "products"
        ][0]["available"]
        == 0
    )


def test_sale_fefo_idempotent_and_historical_receipt(pos):
    open_cash(pos)
    payload = sale_payload(pos, 8)
    first = pos.client.post("/api/pos/sales", json=payload)
    assert first.status_code == 200, first.text
    second = pos.client.post("/api/pos/sales", json=payload)
    assert second.json()["id"] == first.json()["id"]
    with pos.factory.begin() as db:
        assert db.get(InventarioSucursal, pos.inventory_id).stock_fisico == 12
        assert db.get(LoteInventario, pos.early_id).cantidad == 0
        assert db.get(LoteInventario, pos.late_id).cantidad == 12
        assert (
            db.scalar(
                select(func.count())
                .select_from(Venta)
                .where(Venta.id == UUID(payload["request_id"]))
            )
            == 1
        )
        product = db.get(Producto, pos.product_id)
        product.precio_actual = 3000
        product.nombre = "Nombre cambiado"
    receipt = pos.client.get(f"/api/pos/sales/{payload['request_id']}/receipt").json()
    assert receipt["total"] == "8000.00"
    assert receipt["items"][0]["name"] == "Producto transferencia"
    assert "SIN VALIDEZ TRIBUTARIA" in receipt["notice"]
    payload["payment"] = "DEBITO"
    assert pos.client.post("/api/pos/sales", json=payload).status_code == 409


def test_no_oversell_or_manual_price(pos):
    assert (
        pos.client.post(
            "/api/pos/quote",
            json={"items": [{"product_id": str(pos.product_id), "quantity": 21}]},
        ).status_code
        == 409
    )
    assert (
        pos.client.post(
            "/api/pos/quote",
            json={
                "items": [{"product_id": str(pos.product_id), "quantity": 1}],
                "discount": 50,
            },
        ).status_code
        == 422
    )


def test_expired_lot_excluded(pos):
    with pos.factory.begin() as db:
        db.get(LoteInventario, pos.early_id).fecha_vencimiento = datetime.now(
            timezone.utc
        ).date() - timedelta(days=1)
    response = pos.client.get("/api/pos/products", params={"q": str(pos.product_id)})
    assert response.json()["products"][0]["available"] == 15


def test_stale_price_or_stock_rolls_back(pos):
    open_cash(pos)
    data = sale_payload(pos)
    with pos.factory.begin() as db:
        db.get(Producto, pos.product_id).precio_actual = 2000
    assert pos.client.post("/api/pos/sales", json=data).status_code == 409
    with pos.factory() as db:
        assert db.get(Venta, UUID(data["request_id"])) is None
        assert db.get(InventarioSucursal, pos.inventory_id).stock_fisico == 20


def test_mid_transaction_failure_rolls_back(pos, monkeypatch):
    open_cash(pos)
    payload = sale_payload(pos)
    from app.pos.service import PosService

    def fail(*args):
        raise RuntimeError("Simulated failure before commit")

    monkeypatch.setattr(PosService, "receipt_data", fail)
    response = pos.client.post("/api/pos/sales", json=payload)
    assert response.status_code == 500
    assert "Simulated" not in response.text
    with pos.factory() as db:
        assert db.get(Venta, UUID(payload["request_id"])) is None
        assert db.get(InventarioSucursal, pos.inventory_id).stock_fisico == 20
        assert db.get(LoteInventario, pos.early_id).cantidad == 5


def test_close_totals_and_stale_summary(pos):
    cash = open_cash(pos, "1000")
    stale = pos.client.get(f"/api/cash/{cash['id']}/summary").json()
    sell(pos, 2)
    sell(pos, 1, "DEBITO")
    assert (
        pos.client.post(
            f"/api/cash/{cash['id']}/close",
            json={"counted_cash": "3000", "summary_version": stale["version"]},
        ).status_code
        == 409
    )
    summary = pos.client.get(f"/api/cash/{cash['id']}/summary").json()
    assert summary["sales_count"] == 2
    assert summary["average_ticket"] == "1500.00"
    assert summary["expected_cash"] == "3000.00"
    response = pos.client.post(
        f"/api/cash/{cash['id']}/close",
        json={"counted_cash": "2900", "summary_version": summary["version"]},
    )
    assert response.status_code == 200, response.text
    assert response.json()["summary"]["difference"] == "-100.00"
    assert pos.client.get("/api/cash/current").json() is None


@pytest.mark.parametrize("restock,expected", [(True, 19), (False, 18)])
def test_reversal_condition_trace_and_idempotence(pos, restock, expected):
    cash = open_cash(pos)
    receipt = sell(pos)
    payload = reverse_payload(receipt, restock=restock)
    url = f"/api/pos/sales/{receipt['id']}/reversals"
    first = pos.client.post(url, json=payload)
    assert first.status_code == 200, first.text
    assert pos.client.post(url, json=payload).json() == first.json()
    with pos.factory() as db:
        assert db.get(InventarioSucursal, pos.inventory_id).stock_fisico == expected
        movements = db.scalar(
            select(func.count())
            .select_from(MovimientoInventario)
            .where(MovimientoInventario.referencia_id == UUID(first.json()["id"]))
        )
        assert movements == int(restock)
    assert (
        pos.client.get(f"/api/cash/{cash['id']}/summary").json()["expected_cash"]
        == "1000.00"
    )
    payload["request_id"] = str(uuid4())
    payload["items"][0]["quantity"] = 2
    assert pos.client.post(url, json=payload).status_code == 409


def test_reversal_after_closed_cash_uses_new_cash(pos):
    cash = open_cash(pos)
    receipt = sell(pos)
    summary = pos.client.get(f"/api/cash/{cash['id']}/summary").json()
    assert (
        pos.client.post(
            f"/api/cash/{cash['id']}/close",
            json={"counted_cash": "2000", "summary_version": summary["version"]},
        ).status_code
        == 200
    )
    current = open_cash(pos, "2000")
    response = pos.client.post(
        f"/api/pos/sales/{receipt['id']}/reversals", json=reverse_payload(receipt)
    )
    assert response.status_code == 200, response.text
    assert (
        pos.client.get(f"/api/cash/{current['id']}/summary").json()["expected_cash"]
        == "1000.00"
    )
    assert (
        pos.client.get(f"/api/cash/{cash['id']}/summary").json()["expected_cash"]
        == "2000.00"
    )


def test_unauthenticated_and_forbidden(pos):
    pos.client.cookies.clear()
    assert pos.client.get("/api/pos/products").status_code == 401
    assert login(pos, "operator").status_code == 200
    assert pos.client.get("/api/pos/products").status_code == 403


def test_best_promotion_no_stacking_and_expiration():
    now = datetime.now(timezone.utc)
    product, category = uuid4(), uuid4()

    def promotion(code, kind, value, days=1):
        return Promotion(
            code,
            code,
            kind,
            Decimal(value),
            now - timedelta(days=2),
            now + timedelta(days=days),
            product_id=product,
        )

    promotions = (
        promotion("percent", "PERCENT", "20"),
        promotion("fixed", "FIXED_PRICE", "700"),
        promotion("expired", "PERCENT", "99", -1),
    )
    price, selected = best_price(Decimal(1000), product, category, now, promotions)
    assert price == Decimal(700) and selected["code"] == "fixed"
    assert best_price(Decimal(1000), uuid4(), category, now, promotions) == (
        Decimal(1000),
        None,
    )
    assert best_price(Decimal(1000), product, category, now) == (Decimal(1000), None)
