"""E7-H2: concilia pedidos vencidos antes de liberar reservas."""

import logging
from datetime import datetime, timedelta, timezone
from threading import Event
from uuid import UUID

from fastapi import HTTPException
from sqlalchemy import select

from app.orders.models import PedidoOnline
from app.payments.client import MercadoPagoClient, MercadoPagoError
from app.payments.models import CheckoutMercadoPago, PagoMercadoPago
from app.payments.processor import (
    PaymentNotificationService,
    PaymentVerificationError,
    release_reservations,
)
from app.payments.service import lock_order

logger = logging.getLogger(__name__)


class PaymentExpirationService:
    def __init__(self, factory, settings, client=None):
        self.factory = factory
        self.client = client or MercadoPagoClient(settings)
        self.processor = PaymentNotificationService(factory, settings, self.client)
        self.cursor: UUID | None = None

    def run_once(self, stop: Event | None = None, limit=10):
        now = datetime.now(timezone.utc)
        with self.factory() as db:
            query = select(PedidoOnline.id).where(
                PedidoOnline.estado == "PENDIENTE_PAGO",
                PedidoOnline.creado_en <= now - timedelta(minutes=15),
            )
            if self.cursor is not None:
                query = query.where(PedidoOnline.id > self.cursor)
            candidates = list(db.scalars(query.order_by(PedidoOnline.id).limit(limit)))
        if not candidates:
            self.cursor = None
        results = {"cancelled": 0, "paid": 0, "retry": 0, "ignored": 0}
        for identity in candidates:
            if stop is not None and stop.is_set():
                break
            self.cursor = identity
            try:
                result = self.expire(identity, now)
            except (MercadoPagoError, PaymentVerificationError, HTTPException):
                result = "retry"
                logger.warning(
                    "Conciliación pendiente; la reserva se conserva. Pedido %s",
                    identity,
                )
            except Exception:
                # No exponer respuestas del proveedor, secretos ni datos del cliente.
                result = "retry"
                logger.error(
                    "No se pudo conciliar el pedido %s; se reintentará.", identity
                )
            results[result] += 1
        return results

    def expire(self, order_id, now=None):
        now = now or datetime.now(timezone.utc)
        with self.factory.begin() as db:
            lock_order(db, order_id)
            order = db.get(PedidoOnline, order_id)
            if order is None or order.estado != "PENDIENTE_PAGO":
                return "ignored"
            if now < order.creado_en + timedelta(minutes=15):
                return "ignored"
            checkout = db.get(CheckoutMercadoPago, order_id)
            if checkout is None:
                # La creación de checkout toma el mismo bloqueo: después de
                # cancelar no puede crear una preferencia para este pedido.
                release_reservations(db, order)
                return "cancelled"

        account = self.client.get_account()
        if (
            account.get("site_id") != "MLC"
            or "test_user" not in account.get("tags", [])
            or not account.get("id")
        ):
            raise PaymentVerificationError()
        payments = self.client.search_payments(order_id)
        # Priorizar aprobados evita cancelar por un intento rechazado anterior.
        payments.sort(key=lambda row: row.get("status") != "approved")
        for payment in payments:
            self.processor.process(str(payment["id"]))

        with self.factory.begin() as db:
            lock_order(db, order_id)
            order = db.get(PedidoOnline, order_id)
            if order.estado == "PAGADO":
                return "paid"
            if order.estado == "CANCELADO":
                return "cancelled"
            if order.estado != "PENDIENTE_PAGO":
                return "ignored"
            # Releer bajo el bloqueo del pedido: un webhook concurrente puede
            # haber confirmado un pago mientras se consultaba al proveedor.
            latest = self.client.search_payments(order_id)
            known = {str(p["id"]) for p in payments}
            if {str(p["id"]) for p in latest} != known:
                return "retry"
            if any(
                p.get("status")
                not in {"pending", "in_process", "authorized", "rejected", "cancelled"}
                for p in latest
            ):
                return "retry"
            if (
                db.scalar(
                    select(PagoMercadoPago.id)
                    .where(
                        PagoMercadoPago.pedido_id == order_id,
                        PagoMercadoPago.aprobado_en.is_not(None),
                    )
                    .limit(1)
                )
                is not None
            ):
                return "retry"
            release_reservations(db, order)
            return "cancelled"
