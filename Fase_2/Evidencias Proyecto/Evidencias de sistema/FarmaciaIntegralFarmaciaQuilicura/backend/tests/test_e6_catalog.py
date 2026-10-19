"""E6-H1: datos PostgreSQL dentro del rollback de setup; imágenes temporales."""

from io import BytesIO
from uuid import uuid4

import pytest
from app.catalog.images import ProductImages
from app.models import Categoria, InventarioSucursal, Producto, Sucursal
from PIL import Image
from sqlalchemy import select


@pytest.fixture
def public_catalog(setup, tmp_path):
    ids = {
        name: uuid4()
        for name in (
            "category",
            "public",
            "prescription",
            "inactive",
            "hidden",
            "empty_branch",
            "inactive_branch",
        )
    }
    storage = ProductImages(tmp_path)
    picture = BytesIO()
    Image.new("RGB", (20, 20), "white").save(picture, "PNG")
    image_key = storage.save(picture.getvalue())
    setup.app.state.product_images = storage
    with setup.factory.begin() as db:
        db.add(Categoria(id=ids["category"], nombre="Categoria E6 " + setup.suffix))
        db.add_all(
            [
                Sucursal(
                    id=ids["empty_branch"],
                    codigo="E6-" + setup.suffix[:20],
                    nombre="Sucursal sin stock",
                    direccion_local="Prueba",
                    activa=True,
                ),
                Sucursal(
                    id=ids["inactive_branch"],
                    codigo="E6-I-" + setup.suffix[:20],
                    nombre="Sucursal inactiva",
                    direccion_local="Prueba",
                    activa=False,
                ),
            ]
        )
        db.flush()
        for name in ("public", "prescription", "inactive", "hidden"):
            db.add(
                Producto(
                    id=ids[name],
                    sku=f"E6-{name}-{setup.suffix}",
                    nombre=f"E6 {name} {setup.suffix}",
                    descripcion="Información pública de prueba",
                    categoria_id=ids["category"],
                    precio_actual="3990.50",
                    requiere_receta=name == "prescription",
                    activo=name != "inactive",
                    publicado_online=name != "hidden",
                    image_key=image_key,
                )
            )
        db.flush()
        db.add_all(
            [
                InventarioSucursal(
                    producto_id=ids["public"],
                    sucursal_id=setup.ids["branch"],
                    stock_fisico=10,
                    stock_reservado=2,
                ),
                InventarioSucursal(
                    producto_id=ids["prescription"],
                    sucursal_id=setup.ids["branch"],
                    stock_fisico=4,
                    stock_reservado=4,
                ),
                InventarioSucursal(
                    producto_id=ids["public"],
                    sucursal_id=ids["inactive_branch"],
                    stock_fisico=50,
                    stock_reservado=0,
                ),
            ]
        )
    setup.e6_ids = ids
    return setup


def test_anonymous_catalog_filters_and_preserves_prescription(public_catalog):
    ctx = public_catalog
    response = ctx.client.get("/api/ecommerce/products", params={"q": ctx.suffix})
    assert response.status_code == 200
    rows = {row["id"]: row for row in response.json()["products"]}
    assert set(rows) == {str(ctx.e6_ids["public"]), str(ctx.e6_ids["prescription"])}
    regular = rows[str(ctx.e6_ids["public"])]
    assert regular["price"] == "3990.50"
    assert regular["description"] == "Información pública de prueba"
    assert regular["online_purchase_allowed"] is True
    restricted = rows[str(ctx.e6_ids["prescription"])]
    assert restricted["requires_prescription"] is True
    assert restricted["online_purchase_allowed"] is False
    assert "barcodes" not in regular


def test_available_is_informational_and_get_does_not_change_stock(public_catalog):
    ctx = public_catalog
    response = ctx.client.get(
        "/api/ecommerce/products",
        params={"q": ctx.suffix, "branch_id": str(ctx.ids["branch"])},
    )
    assert response.status_code == 200
    rows = response.json()["products"]
    public = next(row for row in rows if row["id"] == str(ctx.e6_ids["public"]))
    assert public["availability"] == [
        {
            "branch_id": str(ctx.ids["branch"]),
            "branch_name": "Sucursal de prueba temporal",
            "available": 8,
        }
    ]
    restricted = next(
        row for row in rows if row["id"] == str(ctx.e6_ids["prescription"])
    )
    assert restricted["availability"][0]["available"] == 0
    with ctx.factory() as db:
        stock = db.scalar(
            select(InventarioSucursal).where(
                InventarioSucursal.producto_id == ctx.e6_ids["public"],
                InventarioSucursal.sucursal_id == ctx.ids["branch"],
            )
        )
        assert (stock.stock_fisico, stock.stock_reservado) == (10, 2)


def test_detail_includes_zero_for_missing_inventory_and_excludes_inactive_branch(
    public_catalog,
):
    ctx = public_catalog
    response = ctx.client.get(f"/api/ecommerce/products/{ctx.e6_ids['public']}")
    assert response.status_code == 200
    availability = {
        row["branch_id"]: row["available"] for row in response.json()["availability"]
    }
    assert availability[str(ctx.e6_ids["empty_branch"])] == 0
    assert str(ctx.e6_ids["inactive_branch"]) not in availability


@pytest.mark.parametrize("name", ["inactive", "hidden"])
def test_private_products_and_images_are_not_public(public_catalog, name):
    url = f"/api/ecommerce/products/{public_catalog.e6_ids[name]}"
    assert public_catalog.client.get(url).status_code == 404
    assert public_catalog.client.get(url + "/image").status_code == 404


def test_image_is_public_and_missing_image_is_404(public_catalog):
    ctx = public_catalog
    url = f"/api/ecommerce/products/{ctx.e6_ids['public']}/image"
    response = ctx.client.get(url)
    assert response.status_code == 200
    assert response.headers["content-type"] == "image/jpeg"
    assert response.headers["cache-control"] == "no-store"
    with ctx.factory.begin() as db:
        db.get(Producto, ctx.e6_ids["public"]).image_key = None
    assert ctx.client.get(url).status_code == 404


def test_branches_are_public_active_and_minimal(public_catalog):
    ctx = public_catalog
    response = ctx.client.get("/api/ecommerce/branches")
    assert response.status_code == 200
    branches = {row["id"]: row for row in response.json()["branches"]}
    assert str(ctx.e6_ids["inactive_branch"]) not in branches
    assert set(branches[str(ctx.ids["branch"])]) == {"id", "name", "address"}


def test_search_escapes_sql_wildcards(public_catalog):
    ctx = public_catalog
    for query in ("%" + ctx.suffix, "_" + ctx.suffix):
        response = ctx.client.get("/api/ecommerce/products", params={"q": query})
        assert response.status_code == 200
        assert response.json()["products"] == []


def test_invalid_or_inactive_branch_and_missing_product(public_catalog):
    ctx = public_catalog
    assert (
        ctx.client.get(
            "/api/ecommerce/products",
            params={"branch_id": str(ctx.e6_ids["inactive_branch"])},
        ).status_code
        == 404
    )
    assert (
        ctx.client.get(
            "/api/ecommerce/products", params={"branch_id": str(uuid4())}
        ).status_code
        == 404
    )
    response = ctx.client.get(
        "/api/ecommerce/products", params={"branch_id": "invalid"}
    )
    assert response.status_code == 422
    assert "sucursal" in response.json()["detail"]
    assert (
        ctx.client.get("/api/ecommerce/products", params={"q": "a" * 151}).status_code
        == 422
    )
    assert ctx.client.get("/api/ecommerce/products/invalid").status_code == 422
    assert ctx.client.get(f"/api/ecommerce/products/{uuid4()}").status_code == 404


def test_public_catalog_does_not_open_admin_or_write_routes(public_catalog):
    ctx = public_catalog
    assert ctx.client.get("/api/products").status_code == 401
    assert ctx.client.get("/api/inventory").status_code == 401
    assert ctx.client.get("/api/branches").status_code == 401
    assert ctx.client.post("/api/ecommerce/products", json={}).status_code == 405
