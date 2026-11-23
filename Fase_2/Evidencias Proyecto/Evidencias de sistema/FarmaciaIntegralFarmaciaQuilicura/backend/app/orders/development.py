"""Simulador local para E7-H3. Completa el retiro sin cobros reales; ventas identificadas como SIMULADO."""
from datetime import datetime, timezone
from typing import Literal
from uuid import UUID

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, ConfigDict
from sqlalchemy import String, select

from app.auth.routes import authenticated_user, check_origin
from app.models import EventoAuditoria, Transferencia, Venta
from app.orders.fulfillment_models import CorreoPedido
from app.orders.models import PedidoOnline
from app.orders.pickup import enqueue_ready
from app.orders.preparation import PAID_STATES
from app.orders.service import summary
from app.orders.transfers import (
    generate_order_transfers,
    lock_order,
    release_order_reservations,
)
from app.payments.models import CheckoutMercadoPago, PagoMercadoPago
from app.payments.processor import register_sale
from app.transfers.service import TransferError

router = APIRouter(prefix="/api/orders/development", tags=["orders-development"])


def enabled(request):
    settings = request.app.state.settings
    return settings.app_environment == "development" and settings.order_payment_simulation


def admin(request):
    if not enabled(request):
        raise HTTPException(404, "Recurso no disponible.")
    actor, _ = authenticated_user(request)
    if "ADMINISTRADOR" not in actor.roles or not actor.is_active:
        raise HTTPException(403, "Solo un administrador puede usar el simulador.")
    return actor


@router.get("/availability")
def availability(request: Request):
    actor, _ = authenticated_user(request)
    return {"enabled": enabled(request) and actor.is_active and "ADMINISTRADOR" in actor.roles}


@router.get("/orders")
def pending_orders(request: Request):
    admin(request)
    with request.app.state.inventory.session_factory() as db:
        rows = db.scalars(select(PedidoOnline).where((PedidoOnline.estado == "PENDIENTE_PAGO") | (
                              PedidoOnline.estado.in_(("PAGADO", "EN_PREPARACION", "LISTO_PARA_RETIRO"))
                              & ~select(Venta.id).where(Venta.pedido_id == PedidoOnline.id).exists()
                              & select(EventoAuditoria.id).where(
                                  EventoAuditoria.origen_actor == "SIMULACION_DESARROLLO",
                                  EventoAuditoria.accion == "E7-H3_PAGO_SIMULADO",
                                  EventoAuditoria.referencia_historica == "Pedido " + PedidoOnline.id.cast(String),
                              ).exists()))
                          .order_by(PedidoOnline.creado_en).limit(100))
        return {"orders": [summary(row) for row in rows]}


class SimulationInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    outcome: Literal["accepted", "failed"]
    confirmed: Literal[True]


@router.post("/orders/{order_id}/payment")
def simulate_payment(order_id: UUID, data: SimulationInput, request: Request):
    actor = admin(request)
    check_origin(request)
    target = "PAGADO" if data.outcome == "accepted" else "CANCELADO"
    try:
        with request.app.state.inventory.session_factory.begin() as db:
            order = lock_order(db, order_id)
            if (db.get(CheckoutMercadoPago, order.id) is not None
                    or db.scalar(select(PagoMercadoPago.id).where(PagoMercadoPago.pedido_id == order.id)) is not None):
                raise HTTPException(409, "Este pedido usa Mercado Pago y no puede simularse. Crea otro pedido de prueba.")
            accepted_retry = data.outcome == "accepted" and order.estado in PAID_STATES
            if order.estado not in ("PENDIENTE_PAGO", target) and not accepted_retry:
                raise HTTPException(409, "El pedido ya tiene un resultado distinto. No se modificó.")
            changed = order.estado != target and not accepted_retry
            if changed:
                order.estado = target
                if data.outcome == "accepted":
                    register_sale(db, order, datetime.now(timezone.utc), simulated=True)
                    db.add(CorreoPedido(pedido_id=order.id, tipo="CONFIRMACION"))
                    generate_order_transfers(db, order)
                else:
                    release_order_reservations(db, order)
                db.add(EventoAuditoria(
                    origen_actor="SIMULACION_DESARROLLO", accion="E7-H3_PAGO_SIMULADO",
                    referencia_historica=f"Pedido {order.id}", usuario_id=actor.id,
                    sucursal_id=order.sucursal_id, ocurrido_en=datetime.now(timezone.utc),
                    datos_cambio={"resultado": target, "simulado": True, "pedido_id": str(order.id)}))
                db.flush()
            if accepted_retry and db.scalar(select(Venta.id).where(Venta.pedido_id == order.id)) is None:
                evidence = db.scalar(select(EventoAuditoria.id).where(
                    EventoAuditoria.origen_actor == "SIMULACION_DESARROLLO",
                    EventoAuditoria.accion == "E7-H3_PAGO_SIMULADO",
                    EventoAuditoria.referencia_historica == f"Pedido {order.id}"))
                if evidence is None or order.estado == "RETIRADO":
                    raise HTTPException(409, "Este pedido no corresponde a una simulación pendiente de completar.")
                previous = order.estado
                register_sale(db, order, datetime.now(timezone.utc), simulated=True)
                order.estado = previous
                if previous == "LISTO_PARA_RETIRO":
                    enqueue_ready(db, order)
                changed = True
                db.add(EventoAuditoria(origen_actor="SIMULACION_DESARROLLO", accion="E7_SIMULACION_COMPLETADA",
                    referencia_historica=f"Pedido {order.id}", usuario_id=actor.id, sucursal_id=order.sucursal_id,
                    datos_cambio={"simulado": True, "pedido_id": str(order.id)}))
                db.flush()
            transfers = list(db.scalars(select(Transferencia).where(Transferencia.pedido_id == order.id)))
            return {"order": summary(order), "transfer_ids": [row.id for row in transfers],
                    "simulated": True, "changed": changed}
    except TransferError as exc:
        raise HTTPException(exc.status, exc.message) from None

