"""E4-H1/H2/H3: API real con PostgreSQL y rollback de datos ficticios."""

from datetime import datetime, timedelta, timezone
from uuid import UUID, uuid4

import pytest
from sqlalchemy import func, select
from test_auth import login

from app.models import (
    Categoria,
    InventarioSucursal,
    LoteInventario,
    MovimientoInventario,
    Permiso,
    Producto,
    Rol,
    Sucursal,
    Transferencia,
    UsuarioInterno,
)

URL = "/api/transfers"
PERMISSIONS = [
    f"transferencias.{action}"
    for action in ("consultar", "solicitar", "autorizar", "despachar", "recibir")
]


@pytest.fixture
def transfer(setup):
    with setup.factory.begin() as db:
        admin = db.get(Rol, setup.ids["admin_role"])
        worker = db.get(Rol, setup.ids["manager_role"])
        receiver = db.get(Rol, setup.ids["operator_role"])
        for code in PERMISSIONS:
            permission = db.scalar(select(Permiso).where(Permiso.codigo == code))
            if permission is None:
                permission = Permiso(codigo=code, descripcion="Prueba E4")
                db.add(permission)
            admin.permisos.append(permission)
            if code != "transferencias.autorizar":
                worker.permisos.append(permission)
                receiver.permisos.append(permission)
        real_admin = db.scalar(select(Rol).where(Rol.codigo == "ADMINISTRADOR"))
        if real_admin is None:
            real_admin = Rol(codigo="ADMINISTRADOR", nombre="Administrador")
            db.add(real_admin)
        admin_user = db.get(UsuarioInterno, setup.ids["admin"])
        admin_user.roles.append(real_admin)
        destination = Sucursal(
            codigo="TD-" + setup.suffix[:20],
            nombre="Destino QA",
            direccion_local="Ficticia",
            activa=True,
        )
        other = Sucursal(
            codigo="TO-" + setup.suffix[:20],
            nombre="Otra QA",
            direccion_local="Ficticia",
            activa=True,
        )
        product = Producto(
            sku="T-" + setup.suffix,
            nombre="Producto transferencia",
            descripcion="",
            categoria=Categoria(nombre="Transferencias QA"),
            precio_actual=1000,
            requiere_receta=False,
            activo=True,
            publicado_online=False,
        )
        db.add_all([destination, other, product])
        db.flush()
        setup.destination_id, setup.other_id, setup.product_id = (
            destination.id,
            other.id,
            product.id,
        )
        db.get(UsuarioInterno, setup.ids["operator"]).sucursal_id = destination.id
        inv = InventarioSucursal(
            producto_id=product.id,
            sucursal_id=setup.ids["branch"],
            stock_fisico=20,
            stock_reservado=0,
        )
        db.add(inv)
        db.flush()
        today = datetime.now(timezone.utc).date()
        early = LoteInventario(
            inventario_sucursal_id=inv.id,
            numero_lote="PRIMERO",
            fecha_vencimiento=today + timedelta(days=10),
            cantidad=5,
        )
        late = LoteInventario(
            inventario_sucursal_id=inv.id,
            numero_lote="SEGUNDO",
            fecha_vencimiento=today + timedelta(days=90),
            cantidad=15,
        )
        db.add_all([early, late])
        db.flush()
        setup.inventory_id, setup.early_id, setup.late_id = inv.id, early.id, late.id
    setup.payload = {
        "request_id": str(uuid4()),
        "origin_id": str(setup.ids["branch"]),
        "destination_id": str(setup.destination_id),
        "items": [{"product_id": str(setup.product_id), "quantity": 8}],
    }
    assert login(setup).status_code == 200
    return setup


def create(ctx, payload=None):
    response = ctx.client.post(URL, json=payload or ctx.payload)
    assert response.status_code == 201, response.text
    return response.json()


def change(ctx, action, body=None):
    return ctx.client.post(
        f"{URL}/{ctx.payload['request_id']}/{action}", json=body or {}
    )


def transit(ctx):
    create(ctx)
    assert change(ctx, "approve").status_code == 200
    assert change(ctx, "dispatch").status_code == 200


def stocks(ctx):
    with ctx.factory() as db:
        row = db.get(InventarioSucursal, ctx.inventory_id)
        return row.stock_fisico, row.stock_reservado, row.stock_disponible


def destination_inventory(db, ctx):
    return db.scalar(
        select(InventarioSucursal).where(
            InventarioSucursal.producto_id == ctx.product_id,
            InventarioSucursal.sucursal_id == ctx.destination_id,
        )
    )


def test_request_reserves_fefo_without_physical_exit(transfer):
    row = create(transfer)
    assert row["state"] == "SOLICITADA"
    assert {lot["number"]: lot["quantity"] for lot in row["items"][0]["lots"]} == {
        "PRIMERO": 5,
        "SEGUNDO": 3,
    }
    assert stocks(transfer) == (20, 8, 12)
    with transfer.factory() as db:
        assert db.get(LoteInventario, transfer.early_id).cantidad == 5
        assert destination_inventory(db, transfer) is None
        movement = db.scalar(
            select(MovimientoInventario).where(
                MovimientoInventario.inventario_sucursal_id == transfer.inventory_id
            )
        )
        assert movement.tipo == "RESERVA" and movement.cantidad_fisica == 0
        assert movement.usuario_id == transfer.ids["admin"]
        assert str(movement.referencia_id) == row["id"]


def test_retry_same_request_reserves_once_and_conflicting_id_fails(transfer):
    create(transfer)
    assert transfer.client.post(URL, json=transfer.payload).status_code == 200
    conflict = transfer.payload | {
        "items": [{"product_id": str(transfer.product_id), "quantity": 9}]
    }
    assert transfer.client.post(URL, json=conflict).status_code == 409
    assert stocks(transfer) == (20, 8, 12)


@pytest.mark.parametrize("quantity", [21, 1_000_000])
def test_insufficient_stock_no_partial_reservation(transfer, quantity):
    transfer.payload["items"][0]["quantity"] = quantity
    assert transfer.client.post(URL, json=transfer.payload).status_code == 409
    assert stocks(transfer) == (20, 0, 20)
    with transfer.factory() as db:
        assert db.get(Transferencia, UUID(transfer.payload["request_id"])) is None


def test_other_reservations_reduce_available(transfer):
    with transfer.factory.begin() as db:
        db.get(InventarioSucursal, transfer.inventory_id).stock_reservado = 15
    assert transfer.client.post(URL, json=transfer.payload).status_code == 409
    assert stocks(transfer) == (20, 15, 5)


def test_two_requests_do_not_allocate_same_lot_units(transfer):
    create(transfer)
    row = create(transfer, transfer.payload | {"request_id": str(uuid4())})
    assert row["items"][0]["lots"] == [
        {
            "number": "SEGUNDO",
            "expiration_date": (
                datetime.now(timezone.utc).date() + timedelta(days=90)
            ).isoformat(),
            "quantity": 8,
        }
    ]
    assert stocks(transfer) == (20, 16, 4)


def test_expired_or_inactive_lots_not_transferable(transfer):
    with transfer.factory.begin() as db:
        db.get(LoteInventario, transfer.early_id).fecha_vencimiento = datetime.now(
            timezone.utc
        ).date()
        db.get(LoteInventario, transfer.late_id).activo = False
    assert transfer.client.post(URL, json=transfer.payload).status_code == 409
    assert stocks(transfer) == (20, 0, 20)
    options = transfer.client.get(URL + "/options").json()
    assert (
        next(
            row
            for row in options["stock"]
            if row["product_id"] == str(transfer.product_id)
        )["available"]
        == 0
    )


def test_approve_retains_reservation_and_reject_releases_once(transfer):
    create(transfer)
    assert change(transfer, "approve").json()["state"] == "AUTORIZADA"
    assert change(transfer, "approve").status_code == 200
    assert stocks(transfer) == (20, 8, 12)
    assert (
        change(transfer, "reject", {"reason": "No se requiere"}).json()["state"]
        == "RECHAZADA"
    )
    assert change(transfer, "reject", {"reason": "No se requiere"}).status_code == 200
    assert stocks(transfer) == (20, 0, 20)
    assert change(transfer, "dispatch").status_code == 409
    with transfer.factory() as db:
        assert (
            db.scalar(
                select(func.count())
                .select_from(MovimientoInventario)
                .where(
                    MovimientoInventario.inventario_sucursal_id == transfer.inventory_id
                )
            )
            == 2
        )


def test_full_flow_preserves_lots_movements_and_no_duplicate_receipt(transfer):
    transit(transfer)
    assert stocks(transfer) == (12, 0, 12)
    assert change(transfer, "dispatch").status_code == 200
    with transfer.factory() as db:
        assert destination_inventory(db, transfer) is None
        assert db.get(LoteInventario, transfer.early_id).cantidad == 0
        assert db.get(LoteInventario, transfer.late_id).cantidad == 12
    assert login(transfer, "operator").status_code == 200
    result = change(transfer, "receive", {"items": transfer.payload["items"]})
    assert result.status_code == 200, result.text
    assert result.json()["state"] == "RECIBIDA" and not result.json()["actions"]
    assert len(result.json()["timeline"]) == 4
    assert (
        change(transfer, "receive", {"items": transfer.payload["items"]}).status_code
        == 200
    )
    with transfer.factory() as db:
        inv = destination_inventory(db, transfer)
        assert (inv.stock_fisico, inv.stock_reservado) == (8, 0)
        assert {lot.numero_lote: lot.cantidad for lot in inv.lotes} == {
            "PRIMERO": 5,
            "SEGUNDO": 3,
        }
        assert (
            len(inv.movimientos) == 1
            and inv.movimientos[0].tipo == "TRANSFERENCIA_ENTRADA"
        )
        assert inv.movimientos[0].usuario_id == transfer.ids["operator"]


def test_mismatched_receipt_stays_in_transit(transfer):
    transit(transfer)
    login(transfer, "operator")
    result = change(
        transfer,
        "receive",
        {"items": [{"product_id": str(transfer.product_id), "quantity": 7}]},
    )
    assert result.status_code == 409
    with transfer.factory() as db:
        assert destination_inventory(db, transfer) is None
        assert (
            db.get(Transferencia, UUID(transfer.payload["request_id"])).estado
            == "EN_TRANSITO"
        )


def test_wrong_state_and_missing_permissions(transfer):
    create(transfer)
    assert change(transfer, "dispatch").status_code == 409
    login(transfer, "manager")
    assert change(transfer, "approve").status_code == 403
    assert change(transfer, "reject", {"reason": "Prueba"}).status_code == 403
    with transfer.factory.begin() as db:
        role = db.get(Rol, transfer.ids["manager_role"])
        role.permisos.append(
            db.scalar(
                select(Permiso).where(Permiso.codigo == "transferencias.autorizar")
            )
        )
    assert change(transfer, "approve").status_code == 403


def test_workers_require_assigned_branch_but_admin_can_receive(transfer):
    create(transfer)
    change(transfer, "approve")
    login(transfer, "operator")
    assert change(transfer, "dispatch").status_code == 403
    login(transfer)
    assert change(transfer, "dispatch").status_code == 200
    login(transfer, "manager")
    assert change(transfer, "receive", {"items": transfer.payload["items"]}).status_code == 403
    login(transfer)
    detail = transfer.client.get(URL + "/" + transfer.payload["request_id"]).json()
    assert "receive" in detail["actions"]
    assert (
        change(transfer, "receive", {"items": transfer.payload["items"]}).status_code
        == 200
    )


def test_admin_from_third_branch_manages_complete_transfer(transfer):
    with transfer.factory.begin() as db:
        db.get(UsuarioInterno, transfer.ids["admin"]).sucursal_id = transfer.other_id
    login(transfer)
    create(transfer)
    assert transfer.payload["request_id"] in {
        row["id"] for row in transfer.client.get(URL).json()["transfers"]
    }
    approved = change(transfer, "approve")
    assert approved.status_code == 200
    assert "dispatch" in approved.json()["actions"]
    dispatched = change(transfer, "dispatch")
    assert dispatched.status_code == 200 and "receive" in dispatched.json()["actions"]
    received = change(transfer, "receive", {"items": transfer.payload["items"]})
    assert received.status_code == 200 and received.json()["state"] == "RECIBIDA"
    with transfer.factory() as db:
        row = db.get(Transferencia, UUID(transfer.payload["request_id"]))
        assert row.despachador_id == row.receptor_id == transfer.ids["admin"]
        assert db.get(UsuarioInterno, transfer.ids["admin"]).sucursal_id == transfer.other_id


def test_worker_scoped_queries_and_create(transfer):
    create(transfer)
    login(transfer, "manager")
    assert transfer.client.get(URL + "/options").json()["origin_ids"] == [
        str(transfer.ids["branch"])
    ]
    assert transfer.payload["request_id"] in {
        r["id"] for r in transfer.client.get(URL).json()["transfers"]
    }
    foreign = transfer.payload | {
        "request_id": str(uuid4()),
        "origin_id": str(transfer.other_id),
    }
    assert transfer.client.post(URL, json=foreign).status_code == 403
    with transfer.factory.begin() as db:
        db.get(UsuarioInterno, transfer.ids["manager"]).sucursal_id = transfer.other_id
    assert transfer.payload["request_id"] not in {
        r["id"] for r in transfer.client.get(URL).json()["transfers"]
    }
    assert (
        transfer.client.get(URL + "/" + transfer.payload["request_id"]).status_code
        == 403
    )


@pytest.mark.parametrize("target", ["branch", "product"])
def test_inactive_data_rejected(transfer, target):
    with transfer.factory.begin() as db:
        if target == "branch":
            db.get(Sucursal, transfer.destination_id).activa = False
        else:
            db.get(Producto, transfer.product_id).activo = False
    assert transfer.client.post(URL, json=transfer.payload).status_code == 409
    assert stocks(transfer) == (20, 0, 20)


@pytest.mark.parametrize(
    "mutation", ["same_branch", "empty", "duplicate", "negative", "decimal", "missing"]
)
def test_input_validation(transfer, mutation):
    data = transfer.payload
    if mutation == "same_branch":
        data["destination_id"] = data["origin_id"]
    elif mutation == "empty":
        data["items"] = []
    elif mutation == "duplicate":
        data["items"] *= 2
    elif mutation == "negative":
        data["items"][0]["quantity"] = -1
    elif mutation == "decimal":
        data["items"][0]["quantity"] = 1.5
    else:
        del data["request_id"]
    result = transfer.client.post(URL, json=data)
    assert result.status_code == 422
    assert isinstance(result.json()["detail"], str)
    assert stocks(transfer) == (20, 0, 20)


def test_authentication_origin_and_unknown_transfer(transfer):
    assert (
        transfer.client.post(
            URL, json=transfer.payload, headers={"Origin": "https://untrusted.invalid"}
        ).status_code
        == 403
    )
    assert transfer.client.get(URL + "/" + str(uuid4())).status_code == 404
    transfer.client.cookies.clear()
    assert transfer.client.get(URL).status_code == 401
    assert transfer.client.post(URL, json=transfer.payload).status_code == 401


def test_pending_transfer_blocks_branch_deactivation_and_hides_delete(transfer):
    create(transfer)
    with transfer.factory.begin() as db:
        db.get(UsuarioInterno, transfer.ids["operator"]).sucursal_id = transfer.other_id
    response = transfer.client.post(
        f"/api/branches/{transfer.destination_id}/deactivate"
    )
    assert response.status_code == 409 and "transferencia" in response.text.lower()
    branches = transfer.client.get("/api/branches").json()["branches"]
    assert not next(b for b in branches if b["id"] == str(transfer.destination_id))[
        "can_delete"
    ]
    change(transfer, "reject", {"reason": "Cancelada"})
    assert (
        transfer.client.post(
            f"/api/branches/{transfer.destination_id}/deactivate"
        ).status_code
        == 200
    )


def test_expired_reserved_lot_cannot_dispatch_but_can_release(transfer):
    create(transfer)
    change(transfer, "approve")
    with transfer.factory.begin() as db:
        db.get(LoteInventario, transfer.early_id).fecha_vencimiento = datetime.now(
            timezone.utc
        ).date()
    assert change(transfer, "dispatch").status_code == 409
    assert stocks(transfer) == (20, 8, 12)
    assert change(transfer, "reject", {"reason": "Lote vencido"}).status_code == 200
    assert stocks(transfer) == (20, 0, 20)


def test_receipt_conflicting_destination_lot_rolls_back(transfer):
    transit(transfer)
    with transfer.factory.begin() as db:
        inv = InventarioSucursal(
            producto_id=transfer.product_id,
            sucursal_id=transfer.destination_id,
            stock_fisico=1,
            stock_reservado=0,
        )
        db.add(inv)
        db.flush()
        db.add(
            LoteInventario(
                inventario_sucursal_id=inv.id,
                numero_lote="SEGUNDO",
                fecha_vencimiento=datetime.now(timezone.utc).date()
                + timedelta(days=200),
                cantidad=1,
            )
        )
    login(transfer, "operator")
    assert (
        change(transfer, "receive", {"items": transfer.payload["items"]}).status_code
        == 409
    )
    with transfer.factory() as db:
        inv = destination_inventory(db, transfer)
        assert inv.stock_fisico == 1 and len(inv.lotes) == 1
        assert (
            db.get(Transferencia, UUID(transfer.payload["request_id"])).estado
            == "EN_TRANSITO"
        )


def test_multiple_products_failure_rolls_back_whole_request(transfer):
    transfer.payload["items"].append({"product_id": str(uuid4()), "quantity": 1})
    assert transfer.client.post(URL, json=transfer.payload).status_code == 409
    assert stocks(transfer) == (20, 0, 20)
    with transfer.factory() as db:
        assert not db.scalar(
            select(func.count())
            .select_from(MovimientoInventario)
            .where(MovimientoInventario.inventario_sucursal_id == transfer.inventory_id)
        )


@pytest.mark.parametrize("scenario", ["last_stock", "same_request", "same_receipt"])
def test_concurrent_operations_on_independent_connections(setup, scenario):
    """Confirma fixtures con UUID exclusivos y elimina solo esos datos al terminar."""
    from concurrent.futures import ThreadPoolExecutor
    from threading import Barrier

    from sqlalchemy import delete

    from app.auth.users import PostgresUserRepository
    from app.db import create_database_engine, create_session_factory
    from app.models import TransferenciaDetalle, TransferenciaLote
    from app.transfers.repository import TransferRepository
    from app.transfers.schemas import CreateTransfer, ReceiveTransfer
    from app.transfers.service import TransferError, TransferService

    engine = create_database_engine()
    factory = create_session_factory(engine)
    origin_id, destination_id, user_id, product_id, category_id, inventory_id = [
        uuid4() for _ in range(6)
    ]
    request_ids = [uuid4(), uuid4()]
    suffix = uuid4().hex
    try:
        with setup.factory() as db:
            test_hash = db.get(UsuarioInterno, setup.ids["admin"]).password_hash
        with factory.begin() as db:
            db.add_all(
                [
                    Sucursal(
                        id=origin_id,
                        codigo="TC1-" + suffix[:16],
                        nombre="QA origen",
                        direccion_local="Ficticia",
                        activa=True,
                    ),
                    Sucursal(
                        id=destination_id,
                        codigo="TC2-" + suffix[:16],
                        nombre="QA destino",
                        direccion_local="Ficticia",
                        activa=True,
                    ),
                    Categoria(id=category_id, nombre="QA concurrencia transferencias"),
                ]
            )
            db.flush()
            db.add(
                Producto(
                    id=product_id,
                    sku="TC-" + suffix,
                    nombre="QA concurrencia",
                    descripcion="",
                    precio_actual=1,
                    categoria_id=category_id,
                    activo=True,
                    requiere_receta=False,
                )
            )
            db.add(
                UsuarioInterno(
                    id=user_id,
                    nombre="QA concurrencia",
                    correo=f"{suffix}@example.com",
                    password_hash=test_hash,
                    sucursal_id=origin_id,
                    activo=True,
                )
            )
            db.flush()
            db.add(
                InventarioSucursal(
                    id=inventory_id,
                    producto_id=product_id,
                    sucursal_id=origin_id,
                    stock_fisico=20,
                    stock_reservado=0,
                )
            )
            db.flush()
            db.add(
                LoteInventario(
                    inventario_sucursal_id=inventory_id,
                    numero_lote="QA",
                    fecha_vencimiento=datetime.now(timezone.utc).date()
                    + timedelta(days=90),
                    cantidad=20,
                )
            )
        actor = (
            PostgresUserRepository(factory)
            .by_id(user_id)
            .model_copy(update={"roles": ["ADMINISTRADOR"], "permissions": PERMISSIONS})
        )
        service = TransferService(TransferRepository(factory))
        payload = {
            "origin_id": origin_id,
            "destination_id": destination_id,
            "items": [{"product_id": product_id, "quantity": 15}],
        }
        barrier = Barrier(2)
        if scenario == "same_receipt":
            service.create(actor, CreateTransfer(**payload, request_id=request_ids[0]))
            service.change(actor, request_ids[0], "approve")
            service.change(actor, request_ids[0], "dispatch")
            actor = actor.model_copy(update={"branch_id": destination_id})

        def execute(index):
            barrier.wait(timeout=10)
            try:
                if scenario == "same_receipt":
                    service.change(
                        actor,
                        request_ids[0],
                        "receive",
                        ReceiveTransfer(items=payload["items"]),
                    )
                    return 200
                request_id = request_ids[index if scenario == "last_stock" else 0]
                _, created = service.create(
                    actor, CreateTransfer(**payload, request_id=request_id)
                )
                return 201 if created else 200
            except TransferError as exc:
                return exc.status

        with ThreadPoolExecutor(max_workers=2) as pool:
            results = sorted(pool.map(execute, range(2)))
        expected = {
            "last_stock": [201, 409],
            "same_request": [200, 201],
            "same_receipt": [200, 200],
        }
        assert results == expected[scenario]
        with factory() as db:
            inv = db.get(InventarioSucursal, inventory_id)
            if scenario == "same_receipt":
                assert (inv.stock_fisico, inv.stock_reservado) == (5, 0)
                dest = db.scalar(
                    select(InventarioSucursal).where(
                        InventarioSucursal.producto_id == product_id,
                        InventarioSucursal.sucursal_id == destination_id,
                    )
                )
                assert dest.stock_fisico == dest.lotes[0].cantidad == 15
                assert len(dest.movimientos) == 1
            else:
                assert (inv.stock_fisico, inv.stock_reservado) == (20, 15)
                assert len(inv.movimientos) == 1
    finally:
        with factory.begin() as db:
            detail_ids = select(TransferenciaDetalle.id).where(
                TransferenciaDetalle.transferencia_id.in_(request_ids)
            )
            inventory_ids = select(InventarioSucursal.id).where(
                InventarioSucursal.producto_id == product_id
            )
            db.execute(
                delete(TransferenciaLote).where(
                    TransferenciaLote.detalle_id.in_(detail_ids)
                )
            )
            db.execute(
                delete(TransferenciaDetalle).where(
                    TransferenciaDetalle.transferencia_id.in_(request_ids)
                )
            )
            db.execute(delete(Transferencia).where(Transferencia.id.in_(request_ids)))
            db.execute(
                delete(MovimientoInventario).where(
                    MovimientoInventario.inventario_sucursal_id.in_(inventory_ids)
                )
            )
            db.execute(
                delete(LoteInventario).where(
                    LoteInventario.inventario_sucursal_id.in_(inventory_ids)
                )
            )
            db.execute(
                delete(InventarioSucursal).where(
                    InventarioSucursal.producto_id == product_id
                )
            )
            db.execute(delete(Producto).where(Producto.id == product_id))
            db.execute(delete(Categoria).where(Categoria.id == category_id))
            db.execute(delete(UsuarioInterno).where(UsuarioInterno.id == user_id))
            db.execute(
                delete(Sucursal).where(Sucursal.id.in_([origin_id, destination_id]))
            )
        engine.dispose()


def test_permission_seed_preserves_customized_roles(setup):
    from app.transfers.seed import seed

    with setup.factory.begin() as db:
        seed(db)
        role = db.scalar(select(Rol).where(Rol.codigo == "ADMINISTRADOR"))
        role.nombre = "Nombre personalizado QA"
        role.permisos = [
            p for p in role.permisos if p.codigo != "transferencias.recibir"
        ]
        db.flush()
        expected = {p.codigo for p in role.permisos}
        seed(db)
        assert role.nombre == "Nombre personalizado QA"
        assert {p.codigo for p in role.permisos} == expected
