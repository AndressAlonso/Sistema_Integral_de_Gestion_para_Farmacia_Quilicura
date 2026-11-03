"""Conexiones independientes: dos entregas o dos trabajadores de correo."""
import os
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
from threading import Barrier
from types import SimpleNamespace
from uuid import uuid4

import pytest
from fastapi import HTTPException
from sqlalchemy import delete, func, select

from app.db import create_database_engine, create_session_factory
from app.models import (
    Categoria,
    InventarioSucursal,
    LoteInventario,
    MovimientoInventario,
    Producto,
    Sucursal,
    UsuarioInterno,
    Venta,
    VentaDetalle,
    VentaLote,
)
from app.orders.fulfillment_models import CorreoPedido, RetiroPedido
from app.orders.mail import MailSettings, OrderMailService
from app.orders.models import PedidoDetalle, PedidoOnline, ReservaPedido
from app.orders.pickup import PickupService, enqueue_ready
from app.payments.models import PagoMercadoPago


@pytest.fixture
def committed_pickup(password_hash):
    if os.environ.get('SIGFQ_TEST_ISOLATED') != '1':
        pytest.skip('Solo base temporal aislada')
    engine = create_database_engine()
    factory = create_session_factory(engine)
    ids = {key: uuid4() for key in ('order', 'branch', 'user', 'product', 'category', 'inventory', 'lot', 'detail', 'sale', 'sale_detail')}
    now = datetime.now(timezone.utc)
    payment_id = str(uuid4().int % 10**18)
    actor = SimpleNamespace(id=ids['user'], name='QA retiro', branch_id=ids['branch'], roles=['ENCARGADO_PEDIDOS'], permissions=['pedidos.consultar', 'pedidos.retirar'], is_active=True)
    try:
        with factory.begin() as db:
            db.add(Sucursal(id=ids['branch'], codigo=str(ids['branch'])[:20], nombre='QA retiro', direccion_local='Ficticia', activa=True))
            db.add(Categoria(id=ids['category'], nombre=str(ids['category'])))
            db.flush()
            db.add(UsuarioInterno(id=ids['user'], nombre=actor.name, correo=f"{ids['user']}@example.com", password_hash=password_hash, activo=True, sucursal_id=ids['branch']))
            db.add(Producto(id=ids['product'], sku=str(ids['product']), nombre='QA producto', descripcion='', categoria_id=ids['category'], precio_actual=100, activo=True, publicado_online=True, requiere_receta=False))
            db.flush()
            db.add(InventarioSucursal(id=ids['inventory'], producto_id=ids['product'], sucursal_id=ids['branch'], stock_fisico=1, stock_reservado=1))
            db.add(PedidoOnline(id=ids['order'], solicitud_hash='a'*64, clave_hash='b'*64, sucursal_id=ids['branch'], nombre='QA invitado', correo='qa@example.com', estado='LISTO_PARA_RETIRO', total=100))
            db.flush()
            db.add(LoteInventario(id=ids['lot'], inventario_sucursal_id=ids['inventory'], numero_lote='QA', cantidad=1, fecha_vencimiento=now.date()+timedelta(days=30), activo=True))
            db.add(PedidoDetalle(id=ids['detail'], pedido_id=ids['order'], producto_id=ids['product'], nombre='QA producto', cantidad=1, precio_unitario=100, precio_base=100, subtotal=100))
            db.add(Venta(id=ids['sale'], pedido_id=ids['order'], solicitud_hash='c'*64, sucursal_id=ids['branch'], medio_pago='MERCADOPAGO', subtotal=100, descuento=0, total=100))
            db.add(PagoMercadoPago(id=payment_id, pedido_id=ids['order'], estado='approved', total=100, moneda='CLP', proveedor_actualizado_en=now, aprobado_en=now))
            db.flush()
            db.add(VentaDetalle(id=ids['sale_detail'], venta_id=ids['sale'], producto_id=ids['product'], nombre='QA producto', sku=str(ids['product']), cantidad=1, precio_base=100, precio_final=100, total=100))
            db.add(ReservaPedido(pedido_id=ids['order'], detalle_id=ids['detail'], lote_id=ids['lot'], cantidad=1, activa=True))
            db.flush()
            enqueue_ready(db, db.get(PedidoOnline, ids['order']))
        with factory() as db:
            code = db.get(RetiroPedido, ids['order']).codigo
        yield factory, actor, ids, code
    finally:
        with factory.begin() as db:
            db.execute(delete(MovimientoInventario).where(MovimientoInventario.inventario_sucursal_id == ids['inventory']))
            db.execute(delete(VentaLote).where(VentaLote.venta_detalle_id == ids['sale_detail']))
            db.execute(delete(VentaDetalle).where(VentaDetalle.venta_id == ids['sale']))
            db.execute(delete(Venta).where(Venta.id == ids['sale']))
            db.execute(delete(PagoMercadoPago).where(PagoMercadoPago.id == payment_id))
            for model in (CorreoPedido, RetiroPedido, ReservaPedido, PedidoDetalle):
                db.execute(delete(model).where(model.pedido_id == ids['order']))
            db.execute(delete(PedidoOnline).where(PedidoOnline.id == ids['order']))
            db.execute(delete(LoteInventario).where(LoteInventario.id == ids['lot']))
            db.execute(delete(InventarioSucursal).where(InventarioSucursal.id == ids['inventory']))
            db.execute(delete(Producto).where(Producto.id == ids['product']))
            db.execute(delete(UsuarioInterno).where(UsuarioInterno.id == ids['user']))
            db.execute(delete(Categoria).where(Categoria.id == ids['category']))
            # La auditoría es inmutable y conserva esta sucursal hasta eliminar
            # la base temporal completa; no se desactivan sus protecciones.
            db.get(Sucursal, ids['branch']).activa = False
        engine.dispose()


def test_concurrent_pickups_deliver_exactly_once(committed_pickup):
    factory, actor, ids, code = committed_pickup
    with factory() as db:
        manual = db.get(RetiroPedido, ids['order']).codigo_manual
    barrier = Barrier(2)
    def collect(index):
        barrier.wait(timeout=10)
        try:
            PickupService(factory).process(actor, code if index == 0 else manual, ids['order'])
            return 200
        except HTTPException as error:
            return error.status_code
    with ThreadPoolExecutor(max_workers=2) as pool:
        assert sorted(pool.map(collect, range(2))) == [200, 409]
    with factory() as db:
        inventory = db.get(InventarioSucursal, ids['inventory'])
        assert (inventory.stock_fisico, inventory.stock_reservado) == (0, 0)
        assert db.scalar(select(func.count()).select_from(VentaLote).where(VentaLote.venta_detalle_id == ids['sale_detail'])) == 1


def test_concurrent_mail_workers_send_once(committed_pickup):
    factory, _, ids, _ = committed_pickup
    barrier, captured = Barrier(2), []
    def deliver():
        barrier.wait(timeout=10)
        return OrderMailService(factory, MailSettings(enabled=True, starttls=False), lambda message, _: captured.append(message)).run_once()
    with ThreadPoolExecutor(max_workers=2) as pool:
        assert sorted(pool.map(lambda _: deliver(), range(2))) == [0, 1]
    assert len(captured) == 1
    with factory() as db:
        assert db.get(PedidoOnline, ids['order']).estado == 'LISTO_PARA_RETIRO'
