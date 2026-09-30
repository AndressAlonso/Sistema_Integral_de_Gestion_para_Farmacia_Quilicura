"""E4-H4/H5: operaciones por lotes existentes, atomicidad y reservas."""

from datetime import datetime, timedelta, timezone
from uuid import UUID, uuid4

import pytest
from sqlalchemy import func, select
from test_auth import login

from app.models import (
    AjusteInventario,
    Categoria,
    InventarioSucursal,
    LoteInventario,
    MovimientoInventario,
    Permiso,
    Producto,
    Rol,
    Sucursal,
    UsuarioInterno,
)

URL = "/api/inventory-adjustments"


@pytest.fixture
def adjustment(setup):
    with setup.factory.begin() as db:
        role = db.get(Rol, setup.ids["admin_role"])
        inventory_role = db.scalar(select(Rol).where(Rol.codigo == "ENCARGADO_INVENTARIO"))
        if inventory_role is None:
            inventory_role = Rol(codigo="ENCARGADO_INVENTARIO", nombre="Encargado de inventario")
            db.add(inventory_role)
        user = db.get(UsuarioInterno, setup.ids["admin"])
        user.roles.append(inventory_role)
        for code in (
            "inventario.ajustar",
            "inventario.registrar_entrada",
            "transferencias.consultar",
            "transferencias.solicitar",
        ):
            permission = db.scalar(select(Permiso).where(Permiso.codigo == code))
            if permission is None:
                permission = Permiso(codigo=code, descripcion="Fixture E4-H5")
                db.add(permission)
            role.permisos.append(permission)
        category = Categoria(nombre="Ajustes QA")
        setup.lot_ids, setup.inventory_ids = [], []
        for index in range(2):
            product = Producto(
                sku=f"ADJ-{index}-{setup.suffix}",
                nombre=f"Producto ajuste {index}",
                descripcion="",
                categoria=category,
                precio_actual=100,
                activo=True,
                requiere_receta=False,
                publicado_online=False,
            )
            db.add(product)
            db.flush()
            inventory = InventarioSucursal(
                producto_id=product.id,
                sucursal_id=setup.ids["branch"],
                stock_fisico=20,
                stock_reservado=0,
            )
            db.add(inventory)
            db.flush()
            lot = LoteInventario(
                inventario_sucursal_id=inventory.id,
                numero_lote=f"ADJ-{index}",
                fecha_vencimiento=datetime.now(timezone.utc).date()
                + timedelta(days=90),
                cantidad=20,
                activo=True,
            )
            db.add(lot)
            db.flush()
            setup.lot_ids.append(lot.id)
            setup.inventory_ids.append(inventory.id)
        other = Sucursal(
            codigo="AJ-" + setup.suffix[:20],
            nombre="Otra QA",
            direccion_local="Ficticia",
            activa=True,
        )
        db.add(other)
        db.flush()
        setup.other_id = other.id
    setup.payload = {
        "request_id": str(uuid4()),
        "branch_id": str(setup.ids["branch"]),
        "reason": "Conteo físico",
        "items": [
            {"lot_id": str(lot_id), "expected_quantity": 20, "new_quantity": value}
            for lot_id, value in zip(setup.lot_ids, [25, 18], strict=True)
        ],
    }
    assert login(setup).status_code == 200
    return setup


def quantities(ctx):
    with ctx.factory() as db:
        return [
            (
                db.get(LoteInventario, lot_id).cantidad,
                db.get(InventarioSucursal, inv_id).stock_fisico,
            )
            for lot_id, inv_id in zip(ctx.lot_ids, ctx.inventory_ids, strict=True)
        ]


def test_permission_without_required_role_cannot_adjust(adjustment):
    with adjustment.factory.begin() as db:
        user = db.get(UsuarioInterno, adjustment.ids["admin"])
        user.roles = [db.get(Rol, adjustment.ids["admin_role"])]
    login(adjustment)
    options = adjustment.client.get("/api/stock-operations/options")
    assert options.status_code == 200
    assert options.json()["can_receive"] and not options.json()["can_adjust"]
    assert adjustment.client.post(URL, json=adjustment.payload).status_code == 403
    assert quantities(adjustment) == [(20, 20), (20, 20)]


@pytest.mark.parametrize("role", ["ADMINISTRADOR", "ENCARGADO_INVENTARIO", "VENDEDOR_CAJERO"])
@pytest.mark.parametrize("has_permission", [False, True])
def test_adjustment_role_and_permission_matrix(role, has_permission):
    from types import SimpleNamespace

    from app.inventory_adjustments.service import AdjustmentError, AdjustmentService

    actor = SimpleNamespace(is_active=True, roles=[role],
                            permissions=["inventario.ajustar"] if has_permission else [], branch_id="own")
    if has_permission and role != "VENDEDOR_CAJERO":
        AdjustmentService.authorize(actor, "own")
        if role == "ADMINISTRADOR":
            AdjustmentService.authorize(actor, "other")
        else:
            with pytest.raises(AdjustmentError):
                AdjustmentService.authorize(actor, "other")
    else:
        with pytest.raises(AdjustmentError):
            AdjustmentService.authorize(actor, "own")


def test_batch_adjustment_records_before_after_lots_and_kardex(adjustment):
    response = adjustment.client.post(URL, json=adjustment.payload)
    assert response.status_code == 201, response.text
    assert quantities(adjustment) == [(25, 25), (18, 18)]
    assert sorted(item["difference"] for item in response.json()["items"]) == [-2, 5]
    assert all(item["previous_quantity"] == 20 for item in response.json()["items"])
    assert adjustment.client.get(URL + "/" + response.json()["id"]).status_code == 200
    assert "solicitud_hash" not in response.text
    with adjustment.factory() as db:
        rows = list(
            db.scalars(
                select(MovimientoInventario).where(
                    MovimientoInventario.referencia_id == UUID(response.json()["id"])
                )
            )
        )
        assert len(rows) == 2
        assert all(
            row.usuario_id == adjustment.ids["admin"]
            and row.tipo == "AJUSTE"
            and row.motivo == "Conteo físico"
            for row in rows
        )


def test_idempotent_retry_and_conflicting_payload(adjustment):
    assert adjustment.client.post(URL, json=adjustment.payload).status_code == 201
    assert adjustment.client.post(URL, json=adjustment.payload).status_code == 200
    assert (
        adjustment.client.post(
            URL, json=adjustment.payload | {"reason": "Otro"}
        ).status_code
        == 409
    )
    assert quantities(adjustment) == [(25, 25), (18, 18)]
    with adjustment.factory() as db:
        assert (
            db.scalar(
                select(func.count())
                .select_from(MovimientoInventario)
                .where(
                    MovimientoInventario.referencia_id
                    == UUID(adjustment.payload["request_id"])
                )
            )
            == 2
        )


@pytest.mark.parametrize(
    "change",
    ["negative", "blank_reason", "duplicate", "empty", "fraction", "unchanged"],
)
def test_validation_no_stock_changes(adjustment, change):
    data = adjustment.payload
    if change == "negative":
        data["items"][0]["new_quantity"] = -1
    elif change == "blank_reason":
        data["reason"] = "   "
    elif change == "duplicate":
        data["items"] *= 2
    elif change == "empty":
        data["items"] = []
    elif change == "fraction":
        data["items"][0]["new_quantity"] = 1.5
    else:
        data["items"][0]["new_quantity"] = 20
    response = adjustment.client.post(URL, json=data)
    assert response.status_code == 422
    assert isinstance(response.json()["detail"], str)
    assert quantities(adjustment) == [(20, 20), (20, 20)]


@pytest.mark.parametrize(
    "invalid", ["stale", "inactive_lot", "inactive_product", "foreign_lot", "reserved"]
)
def test_invalid_row_rolls_back_batch(adjustment, invalid):
    with adjustment.factory.begin() as db:
        ordered = sorted(
            adjustment.lot_ids,
            key=lambda id: str(db.get(LoteInventario, id).inventario.producto_id),
        )
        lot = db.get(LoteInventario, ordered[-1])
        if invalid == "stale":
            lot.cantidad = 19
            lot.inventario.stock_fisico = 19
        elif invalid == "inactive_lot":
            lot.activo = False
        elif invalid == "inactive_product":
            lot.inventario.producto.activo = False
        elif invalid == "foreign_lot":
            lot.inventario.sucursal_id = adjustment.other_id
        else:
            lot.inventario.stock_reservado = 20
            next(
                item
                for item in adjustment.payload["items"]
                if item["lot_id"] == str(lot.id)
            )["new_quantity"] = 1
    before = quantities(adjustment)
    assert adjustment.client.post(URL, json=adjustment.payload).status_code == 409
    assert quantities(adjustment) == before
    with adjustment.factory() as db:
        assert db.get(AjusteInventario, UUID(adjustment.payload["request_id"])) is None
        assert not db.scalar(
            select(func.count())
            .select_from(MovimientoInventario)
            .where(
                MovimientoInventario.referencia_id
                == UUID(adjustment.payload["request_id"])
            )
        )


def test_transfer_reservation_protected_by_lot_even_with_other_stock(adjustment):
    with adjustment.factory.begin() as db:
        inv = db.get(InventarioSucursal, adjustment.inventory_ids[0])
        product_id = inv.producto_id
        inv.stock_fisico += 100
        db.add(
            LoteInventario(
                inventario_sucursal_id=inv.id,
                numero_lote="EXTRA",
                cantidad=100,
                fecha_vencimiento=datetime.now(timezone.utc).date()
                + timedelta(days=150),
            )
        )
    transfer = {
        "request_id": str(uuid4()),
        "origin_id": str(adjustment.ids["branch"]),
        "destination_id": str(adjustment.other_id),
        "items": [{"product_id": str(product_id), "quantity": 10}],
    }
    assert adjustment.client.post("/api/transfers", json=transfer).status_code == 201
    adjustment.payload["items"][0]["new_quantity"] = 9
    assert adjustment.client.post(URL, json=adjustment.payload).status_code == 409
    adjustment.payload["items"][0]["new_quantity"] = 10
    assert adjustment.client.post(URL, json=adjustment.payload).status_code == 201
    with adjustment.factory() as db:
        inv = db.get(InventarioSucursal, adjustment.inventory_ids[0])
        assert (inv.stock_fisico, inv.stock_reservado) == (110, 10)


def test_zero_is_valid_and_expiration_not_changed(adjustment):
    adjustment.payload["items"][0]["new_quantity"] = 0
    with adjustment.factory.begin() as db:
        db.get(LoteInventario, adjustment.lot_ids[0]).fecha_vencimiento = datetime.now(
            timezone.utc
        ).date()
    assert adjustment.client.post(URL, json=adjustment.payload).status_code == 201
    assert quantities(adjustment)[0] == (0, 0)


def test_permissions_branch_and_session_enforced(adjustment):
    assert (
        adjustment.client.post(
            URL, json=adjustment.payload | {"branch_id": str(adjustment.other_id)}
        ).status_code
        == 403
    )
    assert (
        adjustment.client.post(
            URL, json=adjustment.payload, headers={"Origin": "https://invalid.example"}
        ).status_code
        == 403
    )
    login(adjustment, "operator")
    assert adjustment.client.post(URL, json=adjustment.payload).status_code == 403
    assert adjustment.client.get("/api/stock-operations/options").status_code == 403
    adjustment.client.cookies.clear()
    assert adjustment.client.post(URL, json=adjustment.payload).status_code == 401


def test_options_and_receipt_use_existing_lot(adjustment):
    options = adjustment.client.get("/api/stock-operations/options")
    assert options.status_code == 200, options.text
    assert options.json()["can_receive"] and options.json()["can_adjust"]
    assert {b["id"] for b in options.json()["branches"]} == {
        str(adjustment.ids["branch"])
    }
    lots = options.json()["lots"]
    payload = {
        "request_id": str(uuid4()),
        "branch_id": str(adjustment.ids["branch"]),
        "supplier": "Proveedor QA",
        "document_type": "FACTURA",
        "document_number": "QA-1",
        "document_date": datetime.now(timezone.utc).date().isoformat(),
        "items": [
            {
                "product_id": lot["product_id"],
                "lot_number": lot["number"],
                "expiration_date": lot["expiration_date"],
                "quantity": 5,
            }
            for lot in lots
        ],
    }
    response = adjustment.client.post("/api/goods-receipts", json=payload)
    assert response.status_code == 201, response.text
    assert (
        adjustment.client.post("/api/goods-receipts", json=payload).status_code == 200
    )
    assert quantities(adjustment) == [(25, 25), (25, 25)]
    with adjustment.factory() as db:
        assert (
            db.scalar(
                select(func.count())
                .select_from(LoteInventario)
                .where(
                    LoteInventario.inventario_sucursal_id.in_(adjustment.inventory_ids)
                )
            )
            == 2
        )


def test_inactive_branch_and_missing_id(adjustment):
    assert adjustment.client.get(URL + "/" + str(uuid4())).status_code == 404
    with adjustment.factory.begin() as db:
        db.get(Sucursal, adjustment.ids["branch"]).activa = False
    assert adjustment.client.post(URL, json=adjustment.payload).status_code in (
        401,
        409,
    )


def test_seed_preserves_customized_permissions(setup):
    from app.inventory_adjustments.seed import seed

    with setup.factory.begin() as db:
        seed(db)
        role = db.scalar(select(Rol).where(Rol.codigo == "ADMINISTRADOR"))
        role.nombre = "Personalizado"
        role.permisos = [p for p in role.permisos if p.codigo != "inventario.ajustar"]
        db.flush()
        expected = {p.codigo for p in role.permisos}
        seed(db)
        assert role.nombre == "Personalizado"
        assert {p.codigo for p in role.permisos} == expected


@pytest.mark.parametrize("same_request", [True, False])
def test_concurrent_adjustments_independent_connections(setup, same_request):
    """Fixtures confirmados solo para concurrencia; limpieza limitada a UUID propios."""
    from concurrent.futures import ThreadPoolExecutor
    from threading import Barrier

    from sqlalchemy import delete

    from app.auth.users import PostgresUserRepository
    from app.db import create_database_engine, create_session_factory
    from app.inventory_adjustments.repository import AdjustmentRepository
    from app.inventory_adjustments.schemas import CreateAdjustment
    from app.inventory_adjustments.service import AdjustmentError, AdjustmentService
    from app.models import AjusteInventarioDetalle

    engine = create_database_engine()
    factory = create_session_factory(engine)
    branch_id, user_id, product_id, category_id, inv_id, lot_id = [
        uuid4() for _ in range(6)
    ]
    request_ids = [uuid4(), uuid4()]
    suffix = uuid4().hex
    try:
        with setup.factory() as db:
            test_hash = db.get(UsuarioInterno, setup.ids["admin"]).password_hash
        with factory.begin() as db:
            db.add(
                Sucursal(
                    id=branch_id,
                    codigo="AC-" + suffix[:18],
                    nombre="QA ajustes simultáneos",
                    direccion_local="Ficticia",
                    activa=True,
                )
            )
            db.add(Categoria(id=category_id, nombre="QA ajustes simultáneos"))
            db.flush()
            db.add(
                Producto(
                    id=product_id,
                    sku="AC-" + suffix,
                    nombre="QA ajustes",
                    descripcion="",
                    categoria_id=category_id,
                    precio_actual=1,
                    requiere_receta=False,
                    activo=True,
                )
            )
            db.add(
                UsuarioInterno(
                    id=user_id,
                    nombre="QA ajustes",
                    correo=f"{suffix}@example.com",
                    password_hash=test_hash,
                    sucursal_id=branch_id,
                    activo=True,
                )
            )
            db.flush()
            db.add(
                InventarioSucursal(
                    id=inv_id,
                    producto_id=product_id,
                    sucursal_id=branch_id,
                    stock_fisico=20,
                    stock_reservado=0,
                )
            )
            db.flush()
            db.add(
                LoteInventario(
                    id=lot_id,
                    inventario_sucursal_id=inv_id,
                    numero_lote="QA",
                    fecha_vencimiento=datetime.now(timezone.utc).date()
                    + timedelta(days=90),
                    cantidad=20,
                )
            )
        actor = (
            PostgresUserRepository(factory)
            .by_id(user_id)
            .model_copy(update={"permissions": ["inventario.ajustar"], "roles": ["ENCARGADO_INVENTARIO"]})
        )
        service = AdjustmentService(AdjustmentRepository(factory))
        barrier = Barrier(2)

        def adjust(index):
            data = CreateAdjustment(
                request_id=request_ids[0 if same_request else index],
                branch_id=branch_id,
                reason="Conteo concurrente",
                items=[{"lot_id": lot_id, "expected_quantity": 20, "new_quantity": 25}],
            )
            barrier.wait(timeout=10)
            try:
                _, created = service.create(actor, data)
                return 201 if created else 200
            except AdjustmentError as exc:
                return exc.status

        with ThreadPoolExecutor(max_workers=2) as pool:
            results = sorted(pool.map(adjust, range(2)))
        assert results == ([200, 201] if same_request else [201, 409])
        with factory() as db:
            assert db.get(LoteInventario, lot_id).cantidad == 25
            assert db.get(InventarioSucursal, inv_id).stock_fisico == 25
            assert (
                db.scalar(
                    select(func.count())
                    .select_from(MovimientoInventario)
                    .where(MovimientoInventario.inventario_sucursal_id == inv_id)
                )
                == 1
            )
    finally:
        with factory.begin() as db:
            db.execute(
                delete(AjusteInventarioDetalle).where(
                    AjusteInventarioDetalle.ajuste_id.in_(request_ids)
                )
            )
            db.execute(
                delete(AjusteInventario).where(AjusteInventario.id.in_(request_ids))
            )
            db.execute(
                delete(MovimientoInventario).where(
                    MovimientoInventario.inventario_sucursal_id == inv_id
                )
            )
            db.execute(delete(LoteInventario).where(LoteInventario.id == lot_id))
            db.execute(
                delete(InventarioSucursal).where(InventarioSucursal.id == inv_id)
            )
            db.execute(delete(Producto).where(Producto.id == product_id))
            db.execute(delete(Categoria).where(Categoria.id == category_id))
            db.execute(delete(UsuarioInterno).where(UsuarioInterno.id == user_id))
            db.execute(delete(Sucursal).where(Sucursal.id == branch_id))
        engine.dispose()
