"""E5-H3/H5: conexiones PostgreSQL independientes; solo fixtures UUID propios."""

import os
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
from threading import Barrier
from types import SimpleNamespace
from uuid import uuid4

import pytest
from sqlalchemy import delete, select

from app.db import create_database_engine, create_session_factory
from app.models import (
    Categoria,
    InventarioSucursal,
    LoteInventario,
    MovimientoInventario,
    Producto,
    SesionCaja,
    Sucursal,
    UsuarioInterno,
    Venta,
    VentaDetalle,
    VentaLote,
)
from app.pos.repository import PosRepository
from app.pos.schemas import Cart, CloseCash, OpenCash, SaleInput
from app.pos.service import PosError, PosService


@pytest.mark.parametrize(
    "scenario",
    [
        "last_units",
        "different_cash",
        "same_sale",
        "close_vs_sale",
        "same_open",
    ],
)
def test_concurrent_pos(scenario, password_hash):
    if os.environ.get("SIGFQ_TEST_ROLLBACK") != "1":
        pytest.skip("Requiere base local autorizada para fixtures con limpieza")
    engine = create_database_engine()
    factory = create_session_factory(engine)
    branch_id, user_id, product_id, category_id, inventory_id, lot_id = [
        uuid4() for _ in range(6)
    ]
    cash_id = uuid4()
    second_user_id = uuid4()
    sale_ids = [uuid4(), uuid4()]
    actor = SimpleNamespace(
        id=user_id,
        branch_id=branch_id,
        roles=["ADMINISTRADOR"],
        permissions=["pos.operar", "caja.operar"],
    )
    service = PosService(PosRepository(factory))
    try:
        with factory.begin() as db:
            db.add_all(
                [
                    Sucursal(
                        id=branch_id,
                        codigo=f"QP-{str(branch_id)[:20]}",
                        nombre="QA POS",
                        direccion_local="Ficticia",
                        activa=True,
                    ),
                    Categoria(id=category_id, nombre=f"QA POS {category_id}"),
                ]
            )
            db.flush()
            db.add_all(
                [
                    UsuarioInterno(
                        id=user_id,
                        nombre="QA POS",
                        correo=f"{user_id}@example.com",
                        password_hash=password_hash,
                        activo=True,
                        sucursal_id=branch_id,
                    ),
                    Producto(
                        id=product_id,
                        nombre="QA POS",
                        sku=str(product_id),
                        descripcion="",
                        precio_actual=100,
                        categoria_id=category_id,
                        requiere_receta=False,
                        activo=True,
                    ),
                ]
            )
            db.flush()
            db.add(
                InventarioSucursal(
                    id=inventory_id,
                    producto_id=product_id,
                    sucursal_id=branch_id,
                    stock_fisico=5,
                    stock_reservado=0,
                )
            )
            db.flush()
            db.add(
                LoteInventario(
                    id=lot_id,
                    inventario_sucursal_id=inventory_id,
                    numero_lote="QA",
                    cantidad=5,
                    fecha_vencimiento=datetime.now(timezone.utc).date()
                    + timedelta(days=30),
                )
            )
        if scenario != "same_open":
            service.open(actor, OpenCash(request_id=cash_id, initial_amount="0"))
        second_actor = SimpleNamespace(
            id=second_user_id,
            branch_id=branch_id,
            roles=actor.roles,
            permissions=actor.permissions,
        )
        if scenario == "different_cash":
            with factory.begin() as db:
                db.add(
                    UsuarioInterno(
                        id=second_user_id,
                        nombre="QA otro cajero",
                        correo=f"{second_user_id}@example.com",
                        password_hash=password_hash,
                        activo=True,
                        sucursal_id=branch_id,
                    )
                )
            service.open(second_actor, OpenCash(request_id=uuid4(), initial_amount="0"))
        cart = Cart(items=[{"product_id": product_id, "quantity": 5}])
        quote = service.quote(actor, cart)
        summary = (
            service.summary(actor, cash_id) if scenario == "close_vs_sale" else None
        )
        barrier = Barrier(2)

        def run(index):
            barrier.wait(timeout=10)
            try:
                if scenario == "same_open":
                    service.open(
                        actor, OpenCash(request_id=cash_id, initial_amount="0")
                    )
                elif scenario == "close_vs_sale" and index == 1:
                    service.close(
                        actor,
                        cash_id,
                        CloseCash(counted_cash="0", summary_version=summary["version"]),
                    )
                else:
                    service.sell(
                        second_actor
                        if scenario == "different_cash" and index == 1
                        else actor,
                        SaleInput(
                            request_id=sale_ids[
                                0 if scenario == "same_sale" else index
                            ],
                            items=cart.items,
                            payment="EFECTIVO",
                            quote_version=quote["version"],
                        ),
                    )
                return 200
            except PosError as exc:
                return exc.status

        with ThreadPoolExecutor(max_workers=2) as pool:
            results = sorted(pool.map(run, range(2)))
        assert results == (
            [200, 200] if scenario in ("same_sale", "same_open") else [200, 409]
        )
        with factory() as db:
            sales = list(db.scalars(select(Venta).where(Venta.id.in_(sale_ids))))
            stock = db.get(InventarioSucursal, inventory_id).stock_fisico
            assert stock == 5 - 5 * len(sales)
            assert len(sales) <= 1
            assert db.get(LoteInventario, lot_id).cantidad == stock
    finally:
        with factory.begin() as db:
            details = select(VentaDetalle.id).where(VentaDetalle.venta_id.in_(sale_ids))
            db.execute(delete(VentaLote).where(VentaLote.venta_detalle_id.in_(details)))
            db.execute(delete(VentaDetalle).where(VentaDetalle.venta_id.in_(sale_ids)))
            db.execute(delete(Venta).where(Venta.id.in_(sale_ids)))
            db.execute(
                delete(SesionCaja).where(
                    SesionCaja.usuario_id.in_([user_id, second_user_id])
                )
            )
            db.execute(
                delete(MovimientoInventario).where(
                    MovimientoInventario.inventario_sucursal_id == inventory_id
                )
            )
            db.execute(delete(LoteInventario).where(LoteInventario.id == lot_id))
            db.execute(
                delete(InventarioSucursal).where(InventarioSucursal.id == inventory_id)
            )
            db.execute(delete(Producto).where(Producto.id == product_id))
            db.execute(delete(Categoria).where(Categoria.id == category_id))
            db.execute(
                delete(UsuarioInterno).where(
                    UsuarioInterno.id.in_([user_id, second_user_id])
                )
            )
            db.execute(delete(Sucursal).where(Sucursal.id == branch_id))
        engine.dispose()
