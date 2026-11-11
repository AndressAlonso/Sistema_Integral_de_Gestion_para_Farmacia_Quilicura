# ruff: noqa: F811
from datetime import datetime, timedelta, timezone
from uuid import UUID

import pytest
from app.orders.fulfillment_models import CorreoPedido
from app.orders.mail import MailSettings, OrderMailService
from sqlalchemy import select
from test_e6_cart import cart  # noqa: F401
from test_payment_checkout import checkout  # noqa: F401
from test_payment_webhook import notify, webhook  # noqa: F401


def test_confirmed_payment_queues_once_sends_without_qr_and_retries(webhook):
    ctx = webhook
    assert notify(ctx).status_code == 200
    assert notify(ctx).status_code == 200
    order_id=UUID(ctx.payment_order['request_id'])
    with ctx.factory() as db:
        rows=db.scalars(select(CorreoPedido).where(CorreoPedido.pedido_id==order_id, CorreoPedido.tipo=='CONFIRMACION')).all()
        assert len(rows)==1
    def fail(*args):
        raise OSError('SMTP unavailable')
    settings=MailSettings(enabled=True)
    service=OrderMailService(ctx.factory,settings,sender=fail)
    assert service.run_once()==0
    with ctx.factory.begin() as db:
        row=db.scalar(select(CorreoPedido).where(CorreoPedido.pedido_id==order_id))
        assert row.estado=='PENDIENTE' and row.intentos==1
        row.proximo_intento=datetime.now(timezone.utc)-timedelta(seconds=1)
    sent=[]
    service.sender=lambda message, settings: sent.append(message)
    assert service.run_once()==1
    assert service.run_once()==0
    msg=sent[0]
    assert 'confirmado' in msg['Subject']
    assert 'Total pagado:' in msg.get_body(preferencelist=('plain',)).get_content()
    assert 'Sucursal de retiro:' in msg.get_body(preferencelist=('plain',)).get_content()
    assert not list(msg.iter_attachments())
    assert 'Te avisaremos' in msg.get_body(preferencelist=('html',)).get_content()


@pytest.mark.parametrize('status',['rejected','cancelled'])
def test_failed_payment_does_not_queue_confirmation(webhook,status):
    webhook.mp_data['status']=status
    assert notify(webhook).status_code==200
    with webhook.factory() as db:
        assert db.scalar(select(CorreoPedido.id).where(
            CorreoPedido.pedido_id == UUID(webhook.payment_order["request_id"]),
            CorreoPedido.tipo == 'CONFIRMACION',
        )) is None
