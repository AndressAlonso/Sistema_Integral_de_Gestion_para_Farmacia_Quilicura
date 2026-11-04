"""E7-H6: validar y entregar una sola vez, con la misma transacción de stock."""
import hashlib
import re
import secrets
from collections import defaultdict
from datetime import datetime, timezone

from fastapi import HTTPException
from sqlalchemy import select

from app.models import (
    EventoAuditoria,
    MovimientoInventario,
    Venta,
    VentaDetalle,
    VentaLote,
)
from app.orders.fulfillment_models import CorreoPedido, RetiroPedido
from app.orders.preparation import PreparationService
from app.orders.service import summary
from app.orders.transfers import lock_order, reservation_rows
from app.payments.models import PagoMercadoPago


def paid_sale(db, order):
    sale = db.scalar(select(Venta).where(Venta.pedido_id == order.id))
    payments = list(db.scalars(select(PagoMercadoPago).where(PagoMercadoPago.pedido_id == order.id)))
    if (sale is None or sale.total != order.total or not payments
            or not any(p.estado == "approved" and not p.revision_motivo and p.total == order.total for p in payments)
            or any(p.revision_motivo or p.estado in ("refunded", "charged_back", "in_mediation") for p in payments)):
        return None
    return sale


def enqueue_ready(db, order):
    if not paid_sale(db, order):
        return
    if db.get(RetiroPedido, order.id) is None:
        code = "SIGFQ-RETIRO:" + secrets.token_urlsafe(32)
        db.add(RetiroPedido(pedido_id=order.id, codigo=code, codigo_hash=hashlib.sha256(code.encode()).hexdigest()))
        db.add(CorreoPedido(pedido_id=order.id, tipo="LISTO"))


class PickupService:
    def __init__(self, factory):
        self.factory = factory

    @staticmethod
    def authorize(actor, branch=None):
        PreparationService.authorize(actor, branch)
        if ("pedidos.retirar" not in actor.permissions
                or ("ADMINISTRADOR" not in actor.roles and actor.branch_id is None)):
            raise HTTPException(403, "No tienes permiso para registrar retiros en esta sucursal.")

    @staticmethod
    def credential(db, code):
        compact = re.sub(r"[ -]", "", code.strip())
        if re.fullmatch(r"[0-9]{16}", compact):
            row = db.scalar(select(RetiroPedido).where(RetiroPedido.codigo_manual == compact))
            if row is None:
                raise HTTPException(404, "El código de retiro no es válido.")
            return row
        if not re.fullmatch(r"SIGFQ-RETIRO:[A-Za-z0-9_-]{43}", code):
            raise HTTPException(404, "El QR o código de retiro no es válido.")
        row = db.scalar(select(RetiroPedido).where(RetiroPedido.codigo_hash == hashlib.sha256(code.encode()).hexdigest()))
        if row is None:
            raise HTTPException(404, "El código QR no es válido.")
        return row

    def check(self, db, actor, order, credential):
        self.authorize(actor, order.sucursal_id)
        if credential.retirado_en or order.estado == "RETIRADO":
            raise HTTPException(409, "Este pedido ya fue retirado.")
        if order.estado != "LISTO_PARA_RETIRO" or not paid_sale(db, order):
            raise HTTPException(409, "El pedido debe estar pagado y listo para retiro.")
        if not order.sucursal.activa:
            raise HTTPException(409, "La sucursal de retiro está inactiva.")
        problem = PreparationService.ready_problem(db, order, PreparationService.transfers(db, order), lock=True)
        if problem:
            raise HTTPException(409, problem)

    def process(self, actor, code, expected_order_id=None):
        self.authorize(actor)
        with self.factory.begin() as db:
            credential = self.credential(db, code)
            order = lock_order(db, credential.pedido_id)
            db.refresh(credential)
            self.check(db, actor, order, credential)
            if expected_order_id is None:
                return summary(order) | {"customer": {"name": order.nombre, "email": order.correo}}
            if expected_order_id != order.id:
                raise HTTPException(409, "El código no corresponde al pedido revisado.")
            sale = paid_sale(db, order)
            details = {d.producto_id: d for d in db.scalars(select(VentaDetalle).where(VentaDetalle.venta_id == sale.id))}
            quantities = defaultdict(int)
            inventories = {}
            for reserve, lot, inventory in reservation_rows(db, order.id):
                detail = details.get(inventory.producto_id)
                if detail is None:
                    raise HTTPException(409, "Revisa los productos de la venta antes de entregar.")
                lot.cantidad -= reserve.cantidad
                reserve.activa = False
                db.add(VentaLote(venta_detalle_id=detail.id, lote_id=lot.id, cantidad=reserve.cantidad))
                quantities[inventory.id] += reserve.cantidad
                inventories[inventory.id] = inventory
            for inventory_id, quantity in quantities.items():
                inventory = inventories[inventory_id]
                physical, reserved = inventory.stock_fisico, inventory.stock_reservado
                inventory.stock_fisico -= quantity
                inventory.stock_reservado -= quantity
                db.add(MovimientoInventario(inventario_sucursal_id=inventory.id, usuario_id=actor.id,
                    tipo="RETIRO_PEDIDO", cantidad_fisica=-quantity, cantidad_reservada=-quantity,
                    stock_fisico_anterior=physical, stock_fisico_resultante=inventory.stock_fisico,
                    stock_reservado_anterior=reserved, stock_reservado_resultante=inventory.stock_reservado,
                    motivo="Entrega de pedido online", referencia_tipo="PEDIDO_ONLINE", referencia_id=order.id))
            credential.retirado_en = datetime.now(timezone.utc)
            credential.usuario_id, credential.usuario_nombre = actor.id, actor.name
            order.estado = "RETIRADO"
            db.add(EventoAuditoria(origen_actor="USUARIO_INTERNO", accion="E7-H6_RETIRO",
                referencia_historica=f"Pedido {order.id}", usuario_id=actor.id, sucursal_id=order.sucursal_id,
                datos_cambio={"pedido_id": str(order.id), "anterior": "LISTO_PARA_RETIRO", "nuevo": "RETIRADO", "usuario_nombre": actor.name}))
            db.flush()
            return summary(order)
