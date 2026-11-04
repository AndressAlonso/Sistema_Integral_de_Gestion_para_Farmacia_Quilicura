"""E7-H5/H6: pago verificado, correo local, reservas y retiro único."""
# ruff: noqa: F811
from datetime import datetime, timedelta, timezone
from email import policy
from email.parser import BytesParser
from uuid import UUID, uuid4

import pytest
from fastapi import HTTPException
from local_mailbox import local_mailbox
from sqlalchemy import func, select
from test_e6_cart import cart, snapshot  # noqa: F401
from test_payment_checkout import checkout, pay  # noqa: F401
from test_payment_order_integration import actor
from test_payment_webhook import notify, state, webhook  # noqa: F401

from app.models import (
    EventoAuditoria,
    InventarioSucursal,
    LoteInventario,
    MovimientoInventario,
    VentaLote,
)
from app.orders.fulfillment_models import CorreoPedido, RetiroPedido
from app.orders.mail import MailSettings, OrderMailService
from app.orders.models import PedidoOnline
from app.orders.pickup import PickupService
from app.orders.preparation import PreparationService


@pytest.fixture
def ready(webhook):
    ctx = webhook
    assert notify(ctx).status_code == 200
    ctx.order_id = UUID(ctx.payment_order["request_id"])
    ctx.pickup_actor = actor(ctx)
    ctx.pickup_actor.permissions.append("pedidos.retirar")
    preparation = PreparationService(ctx.factory)
    preparation.change(ctx.pickup_actor, ctx.order_id, "preparation", "PAGADO")
    before = snapshot(ctx)
    preparation.change(ctx.pickup_actor, ctx.order_id, "ready", "EN_PREPARACION")
    preparation.change(ctx.pickup_actor, ctx.order_id, "ready", "EN_PREPARACION")
    assert snapshot(ctx) == before
    with ctx.factory() as db:
        ctx.qr = db.get(RetiroPedido, ctx.order_id).codigo
        assert db.scalar(select(func.count()).select_from(CorreoPedido)) == 1
    return ctx


def test_qr_single_delivery_preserves_sale_and_audits(ready):
    ctx = ready
    service = PickupService(ctx.factory)
    before = snapshot(ctx)
    assert service.process(ctx.pickup_actor, ctx.qr)["id"] == ctx.order_id
    assert snapshot(ctx) == before
    result = service.process(ctx.pickup_actor, ctx.qr, ctx.order_id)
    assert result["status"] == "RETIRADO" and state(ctx)["sales"] == 1
    assert state(ctx)["active"] == 0
    with ctx.factory() as db:
        inv = db.get(InventarioSucursal, ctx.cart_ids["destination_inventory"])
        assert inv.stock_fisico == 2 and inv.stock_reservado == 0
        assert db.get(RetiroPedido, ctx.order_id).usuario_id == ctx.pickup_actor.id
        assert db.scalar(select(func.sum(VentaLote.cantidad))) == 1
        assert db.scalar(select(func.count()).select_from(MovimientoInventario).where(MovimientoInventario.tipo == "RETIRO_PEDIDO")) == 1
        assert db.scalar(select(func.count()).select_from(EventoAuditoria).where(EventoAuditoria.accion == "E7-H6_RETIRO")) == 1
        assert ctx.qr not in str(list(db.scalars(select(EventoAuditoria.datos_cambio))))
    after = snapshot(ctx)
    with pytest.raises(HTTPException) as error:
        service.process(ctx.pickup_actor, ctx.qr, ctx.order_id)
    assert error.value.status_code == 409
    assert snapshot(ctx) == after


@pytest.mark.parametrize('separator', ['', ' ', '-'])
def test_manual_code_preserves_leading_zeroes_and_blocks_qr_reuse(ready, separator):
    with ready.factory.begin() as db:
        credential = db.get(RetiroPedido, ready.order_id)
        credential.codigo_manual = '0000123400005678'
    code = separator.join('0000123400005678'[i:i+4] for i in range(0, 16, 4))
    service = PickupService(ready.factory)
    before = snapshot(ready)
    assert service.process(ready.pickup_actor, code)['id'] == ready.order_id
    assert snapshot(ready) == before
    assert service.process(ready.pickup_actor, code, ready.order_id)['status'] == 'RETIRADO'
    after = snapshot(ready)
    for used in (code, ready.qr):
        with pytest.raises(HTTPException) as error:
            service.process(ready.pickup_actor, used, ready.order_id)
        assert error.value.status_code == 409
    assert snapshot(ready) == after and state(ready)['sales'] == 1


def test_qr_collection_also_invalidates_manual_code(ready):
    with ready.factory() as db:
        code = db.get(RetiroPedido, ready.order_id).codigo_manual
    service = PickupService(ready.factory)
    service.process(ready.pickup_actor, ready.qr, ready.order_id)
    with pytest.raises(HTTPException) as error:
        service.process(ready.pickup_actor, code, ready.order_id)
    assert error.value.status_code == 409


def test_manual_code_respects_branch_permissions_and_invalid_code(ready):
    with ready.factory() as db:
        code = db.get(RetiroPedido, ready.order_id).codigo_manual
    before = snapshot(ready)
    service = PickupService(ready.factory)
    with pytest.raises(HTTPException) as error:
        service.process(ready.pickup_actor, 'invalid-numeric-code')
    assert error.value.status_code == 404
    ready.pickup_actor.roles = ['ENCARGADO_PEDIDOS']
    ready.pickup_actor.branch_id = ready.ids['branch']
    with pytest.raises(HTTPException) as error:
        service.process(ready.pickup_actor, code, ready.order_id)
    assert error.value.status_code == 403
    ready.pickup_actor.branch_id = ready.cart_ids['destination']
    ready.pickup_actor.permissions.remove('pedidos.retirar')
    with pytest.raises(HTTPException) as error:
        service.process(ready.pickup_actor, code, ready.order_id)
    assert error.value.status_code == 403
    assert snapshot(ready) == before


def test_rich_mail_embeds_qr_manual_code_and_escapes_customer_data(ready):
    from app.orders.email_templates import manual_label
    captured = []
    with ready.factory.begin() as db:
        order = db.get(PedidoOnline, ready.order_id)
        order.nombre = '<script>cliente</script>'
        order.detalles[0].nombre = '<img src=x onerror=alert(1)>'
    mail = OrderMailService(ready.factory, MailSettings(enabled=True, starttls=False), lambda message, _: captured.append(message))
    assert mail.run_once() == 1
    message = captured[0]
    html = message.get_body(preferencelist=('html',)).get_content()
    plain = message.get_body(preferencelist=('plain',)).get_content()
    assert '<script>' not in html and '&lt;script&gt;cliente&lt;/script&gt;' in html
    assert '<img src=x' not in html and '&lt;img src=x' in html
    assert 'cid:retiro-qr' in html and 'Farmacia Quilicura' in html
    assert any(part.get('Content-ID') == '<retiro-qr>' for part in message.walk())
    with ready.factory() as db:
        credential = db.get(RetiroPedido, ready.order_id)
        assert manual_label(credential.codigo_manual) in plain
        assert credential.codigo == ready.qr
        events = str(list(db.scalars(select(EventoAuditoria.datos_cambio))))
        assert credential.codigo_manual not in events and ready.qr not in events


def test_chilean_money_format():
    from decimal import Decimal

    from app.orders.email_templates import money
    assert money(Decimal(1234567)) == '$1.234.567'
    assert money(Decimal('12.50')) == '$12,50'


def test_verified_payment_to_email_to_manual_pickup_contract(webhook):
    """El proveedor confirma el pago; preparación, correo y retiro ya continúan."""
    import re

    ctx = webhook
    identity = UUID(ctx.payment_order['request_id'])
    user = actor(ctx)
    user.permissions.append('pedidos.retirar')
    assert state(ctx)['order'] == 'PENDIENTE_PAGO'
    assert notify(ctx).status_code == 200
    preparation = PreparationService(ctx.factory)
    preparation.change(user, identity, 'preparation', 'PAGADO')
    assert preparation.change(user, identity, 'ready', 'EN_PREPARACION')['status'] == 'LISTO_PARA_RETIRO'
    with local_mailbox() as (port, captured):
        mail = OrderMailService(ctx.factory, MailSettings(enabled=True, starttls=False, port=port))
        assert mail.run_once() == 1 and mail.run_once() == 0
        assert len(captured) == 1
        message = BytesParser(policy=policy.default).parsebytes(captured[0])
        assert message.get_body(preferencelist=('html',)) is not None
        body = message.get_body(preferencelist=('plain',)).get_content()
        match = re.search(r'Código de retiro: ([0-9 ]+)', body)
        assert match is not None
        number = match.group(1).strip()
        service = PickupService(ctx.factory)
        assert service.process(user, number)['id'] == identity
        assert service.process(user, number, identity)['status'] == 'RETIRADO'
    assert notify(ctx).status_code == 200
    assert state(ctx)['order'] == 'RETIRADO' and state(ctx)['sales'] == 1 and state(ctx)['active'] == 0
    with ctx.factory() as db:
        qr = db.get(RetiroPedido, identity).codigo
    with pytest.raises(HTTPException) as error:
        PickupService(ctx.factory).process(user, qr, identity)
    assert error.value.status_code == 409


@pytest.mark.parametrize("case", ["invalid", "altered", "wrong_order", "wrong_branch", "no_permission", "inactive", "expired_lot", "inactive_lot", "unpaid"])
def test_invalid_pickup_has_no_side_effects(ready, case):
    ctx, code, identity = ready, ready.qr, ready.order_id
    if case == "invalid":
        code = "no-qr"
    if case == "altered":
        code = code[:-1] + ("a" if code[-1] != "a" else "b")
    if case == "wrong_order":
        identity = uuid4()
    if case == "wrong_branch":
        ctx.pickup_actor.roles = ["ENCARGADO_PEDIDOS"]
        ctx.pickup_actor.branch_id = ctx.ids["branch"]
    if case == "no_permission":
        ctx.pickup_actor.permissions.remove("pedidos.retirar")
    if case == "inactive":
        ctx.pickup_actor.is_active = False
    if case in ("expired_lot", "inactive_lot", "unpaid"):
        with ctx.factory.begin() as db:
            lot = db.scalar(select(LoteInventario).where(LoteInventario.inventario_sucursal_id == ctx.cart_ids["destination_inventory"]))
            if case == "expired_lot":
                lot.fecha_vencimiento = datetime.now(timezone.utc).date()
            elif case == "inactive_lot":
                lot.activo = False
            else:
                db.get(PedidoOnline, identity).estado = "REVISION_PAGO"
    before = snapshot(ctx)
    with pytest.raises(HTTPException):
        PickupService(ctx.factory).process(ctx.pickup_actor, code, identity)
    assert snapshot(ctx) == before and state(ctx)["active"] == 1


def test_old_qr_does_not_expire_and_reminder_reuses_it(ready):
    ctx, captured = ready, []
    settings = MailSettings(enabled=True, starttls=False, reminder_enabled=True, reminder_hours=24)
    mail = OrderMailService(ctx.factory, settings, lambda message, _: captured.append(message))
    with ctx.factory.begin() as db:
        db.get(RetiroPedido, ctx.order_id).listo_en = datetime.now(timezone.utc) - timedelta(days=365)
    assert mail.run_once() == 1
    assert mail.run_once() == 1
    assert mail.run_once() == 0
    assert len(captured) == 2
    images = [next(part.get_payload(decode=True) for part in message.iter_attachments() if part.get_content_type() == "image/png") for message in captured]
    assert images[0] == images[1] and images[0].startswith(b"\x89PNG")
    body = captured[0].get_body(preferencelist=('plain',)).get_content()
    assert ctx.pickup_actor.branch_id is not None and "destination" in body and "1 unidad" in body
    receipt = next(part for part in captured[0].iter_attachments() if part.get_content_type() == "text/html")
    assert "SIN VALIDEZ TRIBUTARIA" in receipt.get_payload(decode=True).decode()
    assert PickupService(ctx.factory).process(ctx.pickup_actor, ctx.qr)["status"] == "LISTO_PARA_RETIRO"
    with ctx.factory() as db:
        assert db.get(RetiroPedido, ctx.order_id).codigo == ctx.qr


def test_mail_failure_retries_without_changing_order_or_stock(ready):
    ctx, captured = ready, []
    def fail(message, settings):
        raise OSError("buzón no disponible")
    settings = MailSettings(enabled=True, starttls=False)
    before = snapshot(ctx)
    mail = OrderMailService(ctx.factory, settings, fail)
    assert mail.run_once() == 0 and snapshot(ctx) == before
    assert state(ctx)["order"] == "LISTO_PARA_RETIRO"
    with ctx.factory.begin() as db:
        row = db.scalar(select(CorreoPedido))
        assert row.intentos == 1 and row.estado == "PENDIENTE"
        row.proximo_intento = datetime.now(timezone.utc) - timedelta(seconds=1)
    mail.sender = lambda message, _: captured.append(message)
    assert mail.run_once() == 1 and mail.run_once() == 0 and len(captured) == 1
    assert snapshot(ctx) == before


def test_disabled_reminders_and_pickup_suppresses_pending_mail(ready):
    ctx = ready
    captured = []
    mail = OrderMailService(ctx.factory, MailSettings(enabled=True, starttls=False), lambda message, _: captured.append(message))
    with ctx.factory.begin() as db:
        db.get(RetiroPedido, ctx.order_id).listo_en = datetime.now(timezone.utc) - timedelta(days=365)
    assert mail.run_once() == 1 and mail.run_once() == 0
    with ctx.factory() as db:
        assert db.scalar(select(func.count()).select_from(CorreoPedido)) == 1
    PickupService(ctx.factory).process(ctx.pickup_actor, ctx.qr, ctx.order_id)
    assert mail.run_once() == 0


def test_refund_after_pickup_preserves_delivery_and_stock(ready):
    ctx = ready
    PickupService(ctx.factory).process(ctx.pickup_actor, ctx.qr, ctx.order_id)
    before = snapshot(ctx)
    ctx.mp_data.update(status="refunded", date_last_updated=(datetime.now(timezone.utc) + timedelta(seconds=1)).isoformat())
    assert notify(ctx).status_code == 200
    assert state(ctx)["order"] == "RETIRADO" and state(ctx)["review"]
    assert snapshot(ctx) == before


def test_pickup_failure_rolls_back_stock(ready, monkeypatch):
    import app.orders.pickup as module
    def fail(**kwargs):
        raise RuntimeError("fallo al registrar movimiento")
    monkeypatch.setattr(module, "MovimientoInventario", fail)
    before = snapshot(ready)
    with pytest.raises(RuntimeError):
        PickupService(ready.factory).process(ready.pickup_actor, ready.qr, ready.order_id)
    assert snapshot(ready) == before and state(ready)["active"] == 1
    with ready.factory() as db:
        assert db.get(RetiroPedido, ready.order_id).retirado_en is None


def test_real_smtp_delivery_to_local_inbox(ready):
    with local_mailbox() as (port, captured):
        mail = OrderMailService(ready.factory, MailSettings(enabled=True, starttls=False, host="127.0.0.1", port=port))
        assert mail.run_once() == 1 and mail.run_once() == 0
        assert len(captured) == 1
        message = BytesParser(policy=policy.default).parsebytes(captured[0])
        assert str(message['To']) == "guest@example.com"
        assert {part.get_filename() for part in message.iter_attachments()} == {'QR-retiro.png', 'Comprobante.html'}


def test_http_pickup_requires_permission_and_explicit_confirmation(ready):
    from test_auth import login

    from app.models import Permiso, UsuarioInterno
    ctx = ready
    assert login(ctx).status_code == 200
    response = ctx.client.post('/api/orders/pickup/validate', json={'code': ctx.qr})
    assert response.status_code == 403
    with ctx.factory.begin() as db:
        user = db.get(UsuarioInterno, ctx.ids['admin'])
        role = user.roles[0]
        user.sucursal_id = ctx.cart_ids['destination']
        for code in ('pedidos.consultar', 'pedidos.retirar'):
            permission = db.scalar(select(Permiso).where(Permiso.codigo == code))
            if permission is None:
                permission = Permiso(codigo=code, descripcion=code)
                db.add(permission)
            if permission not in role.permisos:
                role.permisos.append(permission)
    assert ctx.client.post('/api/orders/pickup/validate', json={'code': ctx.qr}).status_code == 200
    before = snapshot(ctx)
    data = {'code': ctx.qr, 'expected_order_id': str(ctx.order_id), 'confirmed': False}
    response = ctx.client.post('/api/orders/pickup/confirm', json=data)
    assert response.status_code == 422 and ctx.qr not in response.text
    assert snapshot(ctx) == before
    data['confirmed'] = True
    assert ctx.client.post('/api/orders/pickup/confirm', json=data).json()['status'] == 'RETIRADO'
    assert ctx.client.post('/api/orders/pickup/confirm', json=data).status_code == 409


def test_pending_mail_is_not_sent_after_collection(ready):
    PickupService(ready.factory).process(ready.pickup_actor, ready.qr, ready.order_id)
    mail = OrderMailService(ready.factory, MailSettings(enabled=True, starttls=False), lambda *_: pytest.fail('No enviar luego del retiro'))
    assert mail.run_once() == 0
    with ready.factory() as db:
        assert db.scalar(select(CorreoPedido)).estado == 'OMITIDO'


def test_disabled_reminders_also_pause_already_queued_reminder(ready):
    with ready.factory.begin() as db:
        db.scalar(select(CorreoPedido)).estado = 'ENVIADO'
        db.add(CorreoPedido(pedido_id=ready.order_id, tipo='RECORDATORIO'))
    mail = OrderMailService(ready.factory, MailSettings(enabled=True, starttls=False), lambda *_: pytest.fail('Recordatorio desactivado'))
    assert mail.run_once() == 0


def test_transferred_order_can_be_collected_only_after_receipt(webhook):
    from test_payment_order_integration import needs_transfer

    from app.models import Transferencia
    from app.transfers.repository import TransferRepository
    from app.transfers.schemas import ReceiveTransfer
    from app.transfers.service import TransferService
    ctx = webhook
    needs_transfer(ctx)
    assert notify(ctx).status_code == 200
    identity = UUID(ctx.payment_order['request_id'])
    user = actor(ctx)
    user.permissions.append('pedidos.retirar')
    preparation = PreparationService(ctx.factory)
    preparation.change(user, identity, 'preparation', 'PAGADO')
    with pytest.raises(HTTPException):
        preparation.change(user, identity, 'ready', 'EN_PREPARACION')
    with ctx.factory() as db:
        transfer_id = db.scalar(select(Transferencia.id).where(Transferencia.pedido_id == identity))
        assert db.get(RetiroPedido, identity) is None
    service = TransferService(TransferRepository(ctx.factory))
    service.change(user, transfer_id, 'dispatch')
    service.change(user, transfer_id, 'receive', ReceiveTransfer(items=[{'product_id': ctx.cart_ids['product'], 'quantity': 1}]))
    preparation.change(user, identity, 'ready', 'EN_PREPARACION')
    with ctx.factory() as db:
        code = db.get(RetiroPedido, identity).codigo
    assert PickupService(ctx.factory).process(user, code, identity)['status'] == 'RETIRADO'
    assert state(ctx)['active'] == 0 and state(ctx)['sales'] == 1
