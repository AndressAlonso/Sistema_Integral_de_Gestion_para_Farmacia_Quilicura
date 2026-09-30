"""E4-H4: recepciones reales sobre PostgreSQL; datos revertidos por fixture."""

from datetime import datetime, timedelta, timezone
from uuid import UUID, uuid4

import pytest
from sqlalchemy import func, select
from test_auth import login

from app.catalog.repository import PostgresCatalogRepository
from app.catalog.schemas import CreateProduct
from app.models import (
    Categoria,
    InventarioSucursal,
    LoteInventario,
    MovimientoInventario,
    Permiso,
    Producto,
    RecepcionMercaderia,
    Rol,
    Sucursal,
)

URL = "/api/goods-receipts"


def test_catalog_creates_no_inventory_until_receipt(receipt):
    with receipt.factory() as db:
        category_id = db.get(Producto, receipt.product_id).categoria_id
    product = PostgresCatalogRepository(receipt.factory).create_product(CreateProduct(
        sku="ZERO-" + receipt.suffix, name="Nuevo sin existencias",
        category_id=category_id, price=100, requires_prescription=False,
    ))
    with receipt.factory.begin() as db:
        records = list(db.scalars(select(InventarioSucursal).where(
            InventarioSucursal.producto_id == product.id,
        )))
        assert records == []
    options = receipt.client.get(URL + "/options").json()
    assert any(p["id"] == str(product.id) for p in options["products"])
    item = receipt.payload["items"][0] | {"product_id": str(product.id), "lot_number": "ZERO-01"}
    assert receipt.client.post(URL, json=receipt.payload | {"items": [item]}).status_code == 201
    with receipt.factory.begin() as db:
        rows = list(db.scalars(select(InventarioSucursal).where(InventarioSucursal.producto_id == product.id)))
        assert len(rows) == 1
        row = rows[0]
        assert row.sucursal_id == receipt.ids["branch"]
        assert row.stock_fisico == 50 and row.stock_reservado == 0
        assert len(row.lotes) == 1 and row.lotes[0].cantidad == 50
        assert len(row.movimientos) == 1


@pytest.fixture
def receipt(setup):
    with setup.factory.begin() as db:
        role = db.get(Rol, setup.ids["admin_role"])
        for code in ("inventario.registrar_entrada", "inventario.gestionar_lotes"):
            permission = db.scalar(select(Permiso).where(Permiso.codigo == code))
            if permission is None:
                permission = Permiso(codigo=code, descripcion="Prueba E4-H4")
                db.add(permission)
            role.permisos.append(permission)
        category = Categoria(nombre="Recepción QA")
        product = Producto(
            sku="R-" + setup.suffix, nombre="Producto recepción", descripcion="",
            categoria=category, precio_actual=1000, requiere_receta=False,
            activo=True, publicado_online=False,
        )
        db.add(product)
        db.flush()
        setup.product_id = product.id
    today = datetime.now(timezone.utc).date()
    setup.payload = {
        "request_id": str(uuid4()), "branch_id": str(setup.ids["branch"]),
        "supplier": "Proveedor ficticio", "document_type": "FACTURA",
        "document_number": "QA-" + setup.suffix, "document_date": today.isoformat(),
        "items": [{"product_id": str(setup.product_id), "lot_number": "QA-001",
                   "expiration_date": (today + timedelta(days=90)).isoformat(), "quantity": 50}],
    }
    assert login(setup).status_code == 200
    return setup


def inventory(db, ctx):
    return db.scalar(select(InventarioSucursal).where(
        InventarioSucursal.producto_id == ctx.product_id,
        InventarioSucursal.sucursal_id == ctx.ids["branch"],
    ))


def test_new_product_receipt_creates_inventory_lot_and_movement(receipt):
    options = receipt.client.get(URL + "/options")
    assert options.status_code == 200
    assert str(receipt.product_id) in {p["id"] for p in options.json()["products"]}
    response = receipt.client.post(URL, json=receipt.payload)
    assert response.status_code == 201, response.text
    assert response.json()["supplier"] == "Proveedor ficticio"
    assert receipt.client.get(URL + "/" + response.json()["id"]).status_code == 200
    with receipt.factory() as db:
        row = inventory(db, receipt)
        assert (row.stock_fisico, row.stock_reservado, row.stock_disponible) == (50, 0, 50)
        assert row.lotes[0].cantidad == 50
        movement = row.movimientos[0]
        assert (movement.stock_fisico_anterior, movement.stock_fisico_resultante) == (0, 50)
        assert movement.usuario_id == receipt.ids["admin"]
        assert str(movement.referencia_id) == receipt.payload["request_id"]


def test_restock_same_lot_preserves_reserved_and_adds_once(receipt):
    assert receipt.client.post(URL, json=receipt.payload).status_code == 201
    with receipt.factory.begin() as db:
        inventory(db, receipt).stock_reservado = 7
    second = receipt.payload | {"request_id": str(uuid4()), "document_number": "Otra factura"}
    assert receipt.client.post(URL, json=second).status_code == 201
    assert receipt.client.post(URL, json=second).status_code == 200
    with receipt.factory() as db:
        row = inventory(db, receipt)
        assert (row.stock_fisico, row.stock_reservado, row.stock_disponible) == (100, 7, 93)
        assert len(row.lotes) == 1 and row.lotes[0].cantidad == 100
        assert len(row.movimientos) == 2


def test_request_id_with_different_data_is_rejected(receipt):
    assert receipt.client.post(URL, json=receipt.payload).status_code == 201
    assert receipt.client.post(URL, json=receipt.payload | {"supplier": "Otro"}).status_code == 409
    with receipt.factory() as db:
        assert inventory(db, receipt).stock_fisico == 50


def test_expiration_conflict_and_multi_item_failure_roll_back(receipt):
    assert receipt.client.post(URL, json=receipt.payload).status_code == 201
    conflict = receipt.payload["items"][0] | {"expiration_date": "2099-01-01"}
    items = [receipt.payload["items"][0] | {"lot_number": "AA-NUEVO"}, conflict]
    payload = receipt.payload | {"request_id": str(uuid4()), "items": items}
    assert receipt.client.post(URL, json=payload).status_code == 409
    with receipt.factory() as db:
        row = inventory(db, receipt)
        assert row.stock_fisico == 50
        assert len(row.lotes) == len(row.movimientos) == 1
        assert db.get(RecepcionMercaderia, UUID(payload["request_id"])) is None


@pytest.mark.parametrize("changes", [
    {"quantity": 0}, {"quantity": -1}, {"quantity": 1.5},
    {"expiration_date": "2000-01-01"}, {"lot_number": " "},
])
def test_invalid_items_do_not_change_stock(receipt, changes):
    payload = receipt.payload | {"items": [receipt.payload["items"][0] | changes]}
    assert receipt.client.post(URL, json=payload).status_code == 422
    with receipt.factory() as db:
        assert inventory(db, receipt) is None


@pytest.mark.parametrize("changes", [{"supplier": " "}, {"document_number": ""}, {"items": []}, {"document_date": "2099-01-01"}])
def test_required_document_data(receipt, changes):
    assert receipt.client.post(URL, json=receipt.payload | changes).status_code == 422


def test_permission_origin_and_branch_scope(receipt):
    assert receipt.client.post(URL, json=receipt.payload, headers={"Origin": "https://invalid.example"}).status_code == 403
    receipt.client.cookies.clear()
    assert receipt.client.post(URL, json=receipt.payload).status_code == 401
    login(receipt, "operator")
    assert receipt.client.post(URL, json=receipt.payload).status_code == 403
    login(receipt)
    with receipt.factory.begin() as db:
        other = Sucursal(codigo="R-" + receipt.suffix[:12], nombre="Otra", direccion_local="Ficticia", activa=True)
        db.add(other)
        db.flush()
        other_id = str(other.id)
    assert receipt.client.post(URL, json=receipt.payload | {"branch_id": other_id}).status_code == 403
    options = receipt.client.get(URL + "/options").json()
    assert {b["id"] for b in options["branches"]} == {str(receipt.ids["branch"])}


@pytest.mark.parametrize("entity", ["branch", "product"])
def test_inactive_references_are_rejected(receipt, entity):
    with receipt.factory.begin() as db:
        if entity == "branch":
            db.get(Sucursal, receipt.ids["branch"]).activa = False
        else:
            db.get(Producto, receipt.product_id).activo = False
    assert receipt.client.post(URL, json=receipt.payload).status_code == 409


def test_legacy_lot_cannot_duplicate_received_units(receipt):
    assert receipt.client.post(URL, json=receipt.payload).status_code == 201
    with receipt.factory() as db:
        inventory_id = str(inventory(db, receipt).id)
    data = {"inventory_id": inventory_id, "lot_number": "DUPLICADO",
            "expiration_date": receipt.payload["items"][0]["expiration_date"], "quantity": 1}
    assert receipt.client.post("/api/inventory/lots", json=data).status_code == 409
    with receipt.factory() as db:
        assert db.scalar(select(func.count()).select_from(LoteInventario).where(
            LoteInventario.inventario_sucursal_id == UUID(inventory_id))) == 1
        assert db.scalar(select(func.count()).select_from(MovimientoInventario).where(
            MovimientoInventario.referencia_id == UUID(receipt.payload["request_id"]))) == 1


@pytest.mark.parametrize("same_request", [False, True])
def test_concurrent_receipts_use_independent_connections(setup, same_request):
    """Solo este caso confirma fixtures temporales; finalmente elimina sus UUID propios."""
    from concurrent.futures import ThreadPoolExecutor
    from threading import Barrier

    from sqlalchemy import delete

    from app.auth.users import PostgresUserRepository
    from app.db import create_database_engine, create_session_factory
    from app.goods_receipts.repository import ReceiptRepository
    from app.goods_receipts.schemas import CreateReceipt
    from app.goods_receipts.service import ReceiptService
    from app.models import RecepcionMercaderiaDetalle, UsuarioInterno

    engine = create_database_engine()
    factory = create_session_factory(engine)
    branch_id, user_id, category_id, product_id = [uuid4() for _ in range(4)]
    suffix = uuid4().hex
    ids = [uuid4(), uuid4()]
    try:
        with setup.factory() as db:
            test_hash = db.get(UsuarioInterno, setup.ids["admin"]).password_hash
        with factory.begin() as db:
            db.add(Sucursal(id=branch_id, codigo="CON-" + suffix[:15], nombre="Concurrencia QA", direccion_local="Ficticia", activa=True))
            db.add(Categoria(id=category_id, nombre="Concurrencia QA"))
            db.flush()
            db.add(Producto(id=product_id, sku="CON-" + suffix, nombre="Concurrencia QA", descripcion="", precio_actual=1, categoria_id=category_id, requiere_receta=False))
            db.add(UsuarioInterno(id=user_id, nombre="Concurrencia QA", correo=f"{suffix}@example.com", password_hash=test_hash, sucursal_id=branch_id, activo=True))
        actor = PostgresUserRepository(factory).by_id(user_id).model_copy(update={"permissions": ["inventario.registrar_entrada"]})
        service = ReceiptService(ReceiptRepository(factory))
        today = datetime.now(timezone.utc).date()
        payload = {
            "branch_id": branch_id, "supplier": "QA", "document_type": "FACTURA",
            "document_number": "QA", "document_date": today,
            "items": [{"product_id": product_id, "quantity": 10, "lot_number": "QA",
                       "expiration_date": today + timedelta(days=90)}],
        }
        barrier = Barrier(2)

        def receive(index):
            data = CreateReceipt(**payload, request_id=ids[0 if same_request else index])
            barrier.wait(timeout=10)
            return service.create(actor, data)

        with ThreadPoolExecutor(max_workers=2) as pool:
            results = list(pool.map(receive, range(2)))
        with factory() as db:
            row = db.scalar(select(InventarioSucursal).where(InventarioSucursal.producto_id == product_id))
            expected = 10 if same_request else 20
            assert row.stock_fisico == row.lotes[0].cantidad == expected
            assert len(row.movimientos) == (1 if same_request else 2)
            assert sum(created for _, created in results) == (1 if same_request else 2)
    finally:
        with factory.begin() as db:
            inv_ids = select(InventarioSucursal.id).where(InventarioSucursal.producto_id == product_id)
            db.execute(delete(RecepcionMercaderiaDetalle).where(RecepcionMercaderiaDetalle.recepcion_id.in_(ids)))
            db.execute(delete(MovimientoInventario).where(MovimientoInventario.inventario_sucursal_id.in_(inv_ids)))
            db.execute(delete(RecepcionMercaderia).where(RecepcionMercaderia.id.in_(ids)))
            db.execute(delete(LoteInventario).where(LoteInventario.inventario_sucursal_id.in_(inv_ids)))
            db.execute(delete(InventarioSucursal).where(InventarioSucursal.producto_id == product_id))
            db.execute(delete(Producto).where(Producto.id == product_id))
            db.execute(delete(Categoria).where(Categoria.id == category_id))
            db.execute(delete(UsuarioInterno).where(UsuarioInterno.id == user_id))
            db.execute(delete(Sucursal).where(Sucursal.id == branch_id))
        engine.dispose()
