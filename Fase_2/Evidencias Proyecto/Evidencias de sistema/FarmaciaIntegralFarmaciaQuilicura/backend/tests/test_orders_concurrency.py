"""E5-H3/H5: conexiones PostgreSQL independientes; solo fixtures UUID propios."""

import os
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
from threading import Barrier
from types import SimpleNamespace
from uuid import uuid4

import pytest
from fastapi import HTTPException
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
from app.orders.models import PedidoDetalle, PedidoOnline, ReservaPedido
from app.orders.schemas import CreateOrder
from app.orders.service import OrderService
from app.pos.repository import PosRepository
from app.pos.schemas import Cart, OpenCash, SaleInput
from app.pos.service import PosError, PosService


@pytest.mark.parametrize("scenario", ["online", "pos"])
def test_last_unit_order_vs_other_channel(scenario, password_hash):
    if os.environ.get("SIGFQ_TEST_ISOLATED") != "1":
        pytest.skip("Solo base temporal aislada")
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
                        publicado_online=True,
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
                    stock_fisico=1,
                    stock_reservado=0,
                )
            )
            db.flush()
            db.add(
                LoteInventario(
                    id=lot_id,
                    inventario_sucursal_id=inventory_id,
                    numero_lote="QA",
                    cantidad=1,
                    fecha_vencimiento=datetime.now(timezone.utc).date()
                    + timedelta(days=30),
                )
            )
        service.open(actor, OpenCash(request_id=cash_id, initial_amount="0"))
        cart = Cart(items=[{"product_id": product_id, "quantity": 1}])
        quote = service.quote(actor, cart)
        orders = OrderService(factory)
        barrier = Barrier(2)

        def run(index):
            barrier.wait(timeout=10)
            try:
                if scenario == "online" or index == 0:
                    orders.create(
                        CreateOrder(
                            request_id=sale_ids[index],
                            request_token=uuid4().hex + uuid4().hex,
                            items=[item.model_dump() for item in cart.items],
                            pickup_branch_id=branch_id,
                            expected_total="100",
                            confirmed=True,
                            guest={"name": "QA invitado", "email": "qa@example.com"},
                        )
                    )
                else:
                    service.sell(
                        actor,
                        SaleInput(
                            request_id=sale_ids[index],
                            items=cart.items,
                            payment="EFECTIVO",
                            quote_version=quote["version"],
                        ),
                    )
                return 200
            except HTTPException as exc:
                return exc.status_code
            except PosError as exc:
                return exc.status

        with ThreadPoolExecutor(max_workers=2) as pool:
            assert sorted(pool.map(run, range(2))) == [200, 409]
        with factory() as db:
            inv = db.get(InventarioSucursal, inventory_id)
            sales = list(db.scalars(select(Venta).where(Venta.id.in_(sale_ids))))
            online = list(
                db.scalars(select(PedidoOnline).where(PedidoOnline.id.in_(sale_ids)))
            )
            assert len(sales) + len(online) == 1
            assert inv.stock_fisico == 1 - len(sales)
            assert inv.stock_reservado == len(online)
            assert db.get(LoteInventario, lot_id).cantidad == inv.stock_fisico
    finally:
        with factory.begin() as db:
            db.execute(
                delete(ReservaPedido).where(ReservaPedido.pedido_id.in_(sale_ids))
            )
            db.execute(
                delete(PedidoDetalle).where(PedidoDetalle.pedido_id.in_(sale_ids))
            )
            db.execute(delete(PedidoOnline).where(PedidoOnline.id.in_(sale_ids)))
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
