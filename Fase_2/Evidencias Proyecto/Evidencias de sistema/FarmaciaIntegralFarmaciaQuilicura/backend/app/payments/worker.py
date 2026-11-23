"""Proceso periódico ligado al arranque y cierre de la API."""

import asyncio
import logging
from contextlib import asynccontextmanager, suppress
from threading import Event

from app.payments.config import PaymentSettings, PaymentWorkerSettings
from app.payments.expiration import PaymentExpirationService

logger = logging.getLogger(__name__)


@asynccontextmanager
async def payment_expiration_worker(factory, *, allow_start=True):
    if not allow_start or not PaymentWorkerSettings().expiration_enabled:
        yield
        return
    settings = PaymentSettings()
    service = PaymentExpirationService(factory, settings)
    stop = Event()
    wake = asyncio.Event()

    async def run():
        while not stop.is_set():
            try:
                counts = await asyncio.to_thread(service.run_once, stop)
                if any(counts.values()):
                    logger.info("Revisión de reservas de pago: %s", counts)
            except Exception:
                logger.error("No se pudo revisar reservas de pago; se reintentará.")
            with suppress(TimeoutError):
                await asyncio.wait_for(wake.wait(), timeout=30)

    task = asyncio.create_task(run(), name="payment-expiration")
    logger.info("Revisión automática de reservas de pago activada.")
    try:
        yield
    finally:
        stop.set()
        wake.set()
        # Espera la transacción en curso antes de cerrar el motor de BD.
        await task
