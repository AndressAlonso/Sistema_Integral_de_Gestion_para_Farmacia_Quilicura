"""E7-H5: SMTP configurable, comprobante y el mismo QR en cada envío."""
import asyncio
import io
import smtplib
import ssl
from contextlib import asynccontextmanager, suppress
from datetime import datetime, timedelta, timezone
from email.message import EmailMessage
from threading import Event

import qrcode
from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict
from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError

from app.config import BACKEND_DIR
from app.models import EventoAuditoria
from app.orders.email_templates import manual_label, money, ready_email, receipt_html
from app.orders.fulfillment_models import CorreoPedido, RetiroPedido
from app.orders.models import PedidoOnline
from app.orders.pickup import enqueue_ready, paid_sale
from app.orders.service import summary
from app.orders.transfers import lock_order


class MailSettings(BaseSettings):
    model_config = SettingsConfigDict(env_file=BACKEND_DIR / ".env", env_prefix="ORDER_MAIL_", extra="ignore", hide_input_in_errors=True)
    enabled: bool = False
    host: str = "127.0.0.1"
    port: int = Field(default=1025, ge=1, le=65535)
    sender: str = "pedidos@farmacia.example"
    username: str | None = None
    password: SecretStr | None = None
    starttls: bool = True
    ssl: bool = False
    reminder_enabled: bool = False
    reminder_hours: int = Field(default=24, ge=1, le=8760)


def message_for(order, credential, outbox, settings, sale):
    data = summary(order)
    number = data["number"]
    title = "Tu pedido está listo para retiro" if outbox.tipo == "LISTO" else "Recordatorio: tu pedido sigue listo para retiro"
    products = "\n".join(f"• {d.nombre}: {d.cantidad} {'unidad' if d.cantidad == 1 else 'unidades'} · {money(d.subtotal)}" for d in order.detalles)
    msg = EmailMessage()
    msg["From"], msg["To"] = settings.sender, order.correo
    msg["Subject"] = f"{title} · {number}"
    msg["Message-ID"] = f"<pedido-{outbox.id}@sigfq.local>"
    msg.set_content(f"Hola {order.nombre},\n\n{title}.\nPedido: {number}\nSucursal: {order.sucursal.nombre}\n{products}\nTotal: {money(order.total)}\n\nCódigo de retiro: {manual_label(credential.codigo_manual)}\nPresenta el QR adjunto o dicta este código al personal al retirar. Ambos sirven para un único retiro y no vencen por el paso del tiempo.\nIncluimos tu comprobante interno sin validez tributaria.")
    image = io.BytesIO()
    qrcode.make(credential.codigo).save(image, format="PNG")
    msg.add_alternative(ready_email(order, number, title, credential.codigo_manual), subtype="html")
    msg.get_payload()[-1].add_related(image.getvalue(), maintype="image", subtype="png", cid="<retiro-qr>", disposition="inline")
    msg.add_attachment(image.getvalue(), maintype="image", subtype="png", filename="QR-retiro.png")
    receipt = receipt_html(order, number, sale)
    msg.add_attachment(receipt.encode("utf-8"), maintype="text", subtype="html", filename="Comprobante.html")
    return msg


def send_smtp(message, settings):
    if settings.username and not (settings.starttls or settings.ssl):
        raise ValueError("La autenticación SMTP requiere TLS.")
    client = smtplib.SMTP_SSL if settings.ssl else smtplib.SMTP
    kwargs = {"context": ssl.create_default_context()} if settings.ssl else {}
    with client(settings.host, settings.port, timeout=10, **kwargs) as smtp:
        if settings.starttls and not settings.ssl:
            smtp.starttls(context=ssl.create_default_context())
        if settings.username:
            smtp.login(settings.username, settings.password.get_secret_value() if settings.password else "")
        smtp.send_message(message)


class OrderMailService:
    def __init__(self, factory, settings=None, sender=send_smtp):
        self.factory, self.settings, self.sender = factory, settings or MailSettings(), sender

    def schedule_reminders(self, now):
        if not self.settings.reminder_enabled:
            return
        with self.factory() as db:
            ids = list(db.scalars(select(RetiroPedido.pedido_id).join(PedidoOnline).where(
                PedidoOnline.estado == "LISTO_PARA_RETIRO", RetiroPedido.retirado_en.is_(None),
                RetiroPedido.listo_en <= now - timedelta(hours=self.settings.reminder_hours)).limit(100)))
        for identity in ids:
            with self.factory.begin() as db:
                order = lock_order(db, identity)
                ready = db.scalar(select(CorreoPedido).where(CorreoPedido.pedido_id == identity, CorreoPedido.tipo == "LISTO"))
                exists = db.scalar(select(CorreoPedido.id).where(CorreoPedido.pedido_id == identity, CorreoPedido.tipo == "RECORDATORIO"))
                if order.estado == "LISTO_PARA_RETIRO" and paid_sale(db, order) and ready and ready.estado == "ENVIADO" and not exists:
                    db.add(CorreoPedido(pedido_id=identity, tipo="RECORDATORIO"))

    def run_once(self, stop=None):
        if not self.settings.enabled:
            return 0
        now = datetime.now(timezone.utc)
        # Incluye pedidos que ya estaban listos al instalar esta versión.
        with self.factory() as db:
            missing = list(db.scalars(select(PedidoOnline.id).outerjoin(RetiroPedido).where(
                PedidoOnline.estado == "LISTO_PARA_RETIRO", RetiroPedido.pedido_id.is_(None)).limit(100)))
        for identity in missing:
            with self.factory.begin() as db:
                order = lock_order(db, identity)
                if order.estado == "LISTO_PARA_RETIRO":
                    enqueue_ready(db, order)
        self.schedule_reminders(now)
        with self.factory() as db:
            rows = list(db.execute(select(CorreoPedido.id, CorreoPedido.pedido_id).where(
                CorreoPedido.estado == "PENDIENTE", CorreoPedido.proximo_intento <= now).order_by(CorreoPedido.proximo_intento).limit(50)))
        sent = 0
        for identity, order_id in rows:
            if stop and stop.is_set():
                break
            with self.factory.begin() as db:
                order = lock_order(db, order_id)
                row = db.scalar(select(CorreoPedido).where(CorreoPedido.id == identity).with_for_update(skip_locked=True))
                if row is None or row.estado != "PENDIENTE" or row.proximo_intento > now:
                    continue
                if row.tipo == "RECORDATORIO" and not self.settings.reminder_enabled:
                    continue
                credential = db.get(RetiroPedido, order_id)
                if not credential or credential.retirado_en or order.estado != "LISTO_PARA_RETIRO" or not paid_sale(db, order):
                    row.estado = "OMITIDO"
                    continue
                row.intentos += 1
                try:
                    self.sender(message_for(order, credential, row, self.settings, paid_sale(db, order)), self.settings)
                except (OSError, smtplib.SMTPException, ValueError):
                    row.proximo_intento = now + timedelta(minutes=min(60, 2 ** min(row.intentos, 6)))
                    continue
                row.estado, row.enviado_en = "ENVIADO", datetime.now(timezone.utc)
                db.add(EventoAuditoria(origen_actor="SISTEMA", accion="E7-H5_CORREO",
                    referencia_historica=f"Pedido {order.id}", sucursal_id=order.sucursal_id,
                    datos_cambio={"tipo": row.tipo, "resultado": "ENVIADO"}))
                sent += 1
        return sent


@asynccontextmanager
async def order_mail_worker(factory, *, allow_start=True):
    settings = MailSettings()
    if not allow_start or not settings.enabled:
        yield
        return
    service, stop, wake = OrderMailService(factory, settings), Event(), asyncio.Event()

    async def run():
        import logging
        while not stop.is_set():
            try:
                await asyncio.to_thread(service.run_once, stop)
            except (SQLAlchemyError, OSError, ValueError):
                logging.getLogger(__name__).error("No se pudieron enviar los correos de pedidos; se reintentará.")
            with suppress(TimeoutError):
                await asyncio.wait_for(wake.wait(), timeout=30)

    task = asyncio.create_task(run(), name="order-mail")
    try:
        yield
    finally:
        stop.set()
        wake.set()
        await task
