"""E2-H1: pruebas con PostgreSQL y archivos temporales; no toca fotos reales."""

from io import BytesIO
from uuid import UUID, uuid4

import pytest
from app.catalog.images import MAX_BYTES, ProductImages
from app.models import CodigoBarra, Permiso, Rol
from PIL import Image, PngImagePlugin
from sqlalchemy import select
from test_auth import login


@pytest.fixture
def catalog(setup, tmp_path):
    with setup.factory.begin() as db:
        permission = db.scalar(
            select(Permiso).where(Permiso.codigo == "catalogo.gestionar")
        )
        if permission is None:
            permission = Permiso(
                codigo="catalogo.gestionar", descripcion="Prueba catalogo"
            )
            db.add(permission)
        role = db.get(Rol, setup.ids["admin_role"])
        role.permisos.append(permission)
    setup.app.state.product_images = ProductImages(tmp_path)
    login(setup)
    category = setup.client.post(
        "/api/categories", json={"name": "Categoria QA"}
    ).json()
    setup.payload = {
        "sku": "QA-" + setup.suffix[:12],
        "name": "Producto QA",
        "description": "Prueba",
        "category_id": category["id"],
        "price": "1990.50",
        "requires_prescription": False,
        "is_active": True,
        "published_online": False,
        "barcodes": ["000" + setup.suffix],
    }
    setup.product = setup.client.post("/api/products", json=setup.payload).json()
    setup.url = "/api/products/" + setup.product["id"]
    return setup


def picture(fmt="PNG", size=(40, 60)):
    output = BytesIO()
    image = Image.new("RGB", size, "#70a030")
    info = PngImagePlugin.PngInfo()
    info.add_text("Private", "must not survive")
    image.save(output, fmt, pnginfo=info if fmt == "PNG" else None)
    return output.getvalue()


def editable(catalog, **changes):
    return {
        key: value
        for key, value in (catalog.payload | changes).items()
        if key != "price"
    }


def test_edit_retains_price_and_unchanged_barcode_id(catalog):
    with catalog.factory() as db:
        old = db.scalar(
            select(CodigoBarra.id).where(
                CodigoBarra.producto_id == UUID(catalog.product["id"])
            )
        )
    result = catalog.client.patch(
        catalog.url,
        json=editable(
            catalog,
            name="Editado",
            barcodes=[*catalog.payload["barcodes"], "001" + catalog.suffix],
        ),
    )
    assert result.status_code == 200
    assert result.json()["price"] == "1990.50"
    with catalog.factory() as db:
        assert db.get(CodigoBarra, old) is not None
    assert catalog.client.get(catalog.url).json()["name"] == "Editado"
    assert (
        catalog.client.patch(
            catalog.url, json=editable(catalog) | {"price": "1"}
        ).status_code
        == 422
    )
    assert (
        catalog.client.patch(catalog.url, json=editable(catalog, barcodes=[])).json()[
            "barcodes"
        ]
        == []
    )


def test_duplicate_rolls_back_all_edits(catalog):
    other = catalog.payload | {
        "sku": "OTHER-" + catalog.suffix[:12],
        "barcodes": ["002" + catalog.suffix],
    }
    assert catalog.client.post("/api/products", json=other).status_code == 201
    response = catalog.client.patch(
        catalog.url,
        json=editable(catalog, name="No guardar", barcodes=other["barcodes"]),
    )
    assert response.status_code == 409
    row = catalog.client.get(catalog.url).json()
    assert row["name"] == catalog.payload["name"]
    assert row["barcodes"] == catalog.payload["barcodes"]


@pytest.mark.parametrize("fmt", ["PNG", "JPEG", "WEBP"])
def test_upload_normalizes_and_serves_image(catalog, fmt):
    result = catalog.client.post(
        catalog.url + "/image",
        content=picture(fmt),
        headers={"Content-Type": "application/octet-stream"},
    )
    assert result.status_code == 200
    assert result.json()["image_url"].startswith(catalog.url + "/image?v=")
    image = catalog.client.get(result.json()["image_url"])
    assert image.status_code == 200
    assert image.headers["content-type"] == "image/jpeg"
    with Image.open(BytesIO(image.content)) as output:
        assert output.format == "JPEG"
        assert "Private" not in output.info
    assert (
        catalog.client.get(catalog.url).json()["image_url"]
        == result.json()["image_url"]
    )


def test_replace_remove_and_invalid_upload_preserves_image(catalog, tmp_path):
    first = catalog.client.post(catalog.url + "/image", content=picture()).json()
    assert len(list(tmp_path.glob("*.jpg"))) == 1
    assert (
        catalog.client.post(catalog.url + "/image", content=b"<svg></svg>").status_code
        == 415
    )
    assert catalog.client.get(catalog.url).json()["image_url"] == first["image_url"]
    second = catalog.client.post(catalog.url + "/image", content=picture("JPEG")).json()
    assert second["image_url"] != first["image_url"]
    assert len(list(tmp_path.glob("*.jpg"))) == 1
    assert (
        catalog.client.post(catalog.url + "/image/remove").json()["image_url"] is None
    )
    assert catalog.client.get(catalog.url + "/image").status_code == 404
    assert not list(tmp_path.glob("*.jpg"))


def test_size_and_invalid_image_rejection(catalog):
    assert catalog.client.post(catalog.url + "/image", content=b"").status_code == 413
    assert (
        catalog.client.post(
            catalog.url + "/image", content=b"x" * (MAX_BYTES + 1)
        ).status_code
        == 413
    )
    assert (
        catalog.client.post(
            catalog.url + "/image", content=picture(size=(5000, 4100))
        ).status_code
        == 413
    )
    assert (
        catalog.client.post(catalog.url + "/image", content=picture("GIF")).status_code
        == 415
    )
    assert (
        catalog.client.post(catalog.url + "/image", content=picture()[:20]).status_code
        == 415
    )


def test_auth_permission_origin_and_missing_product(catalog):
    assert (
        catalog.client.post(
            catalog.url + "/image",
            content=picture(),
            headers={"Origin": "https://invalid.test"},
        ).status_code
        == 403
    )
    assert (
        catalog.client.post(
            "/api/products/" + str(uuid4()) + "/image", content=picture()
        ).status_code
        == 404
    )
    with catalog.factory.begin() as db:
        db.get(Rol, catalog.ids["admin_role"]).permisos = []
    assert catalog.client.patch(catalog.url, json=editable(catalog)).status_code == 403
    assert catalog.client.get(catalog.url + "/image").status_code == 403
    catalog.client.cookies.clear()
    assert (
        catalog.client.post(catalog.url + "/image", content=picture()).status_code
        == 401
    )


def test_storage_failure_does_not_change_existing_reference(
    catalog, monkeypatch, tmp_path
):
    first = catalog.client.post(catalog.url + "/image", content=picture()).json()

    def fail(*args):
        raise RuntimeError("Simulated database failure")

    monkeypatch.setattr(catalog.app.state.catalog, "set_image", fail)
    assert (
        catalog.client.post(catalog.url + "/image", content=picture()).status_code
        == 500
    )
    assert catalog.client.get(catalog.url).json()["image_url"] == first["image_url"]
    assert len(list(tmp_path.glob("*.jpg"))) == 1


def test_unexpected_failure_rolls_back_edit(catalog, monkeypatch):
    repository = catalog.app.state.catalog
    original = repository.response
    def fail(row):
        raise RuntimeError("Failure after flush")
    monkeypatch.setattr(repository, "response", fail)
    result = catalog.client.patch(catalog.url, json=editable(catalog, name="Do not keep", barcodes=[]))
    assert result.status_code == 500
    monkeypatch.setattr(repository, "response", original)
    row = catalog.client.get(catalog.url).json()
    assert row["name"] == catalog.payload["name"]
    assert row["barcodes"] == catalog.payload["barcodes"]
