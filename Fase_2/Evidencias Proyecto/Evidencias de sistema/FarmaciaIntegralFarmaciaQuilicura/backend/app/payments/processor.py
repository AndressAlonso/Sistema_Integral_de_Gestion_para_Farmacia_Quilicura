"""E7-H2: confirmación autoritativa, venta única y reservas transaccionales."""

from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
from hashlib import sha256
from uuid import UUID, uuid4

from fastapi import HTTPException
from sqlalchemy import func, select, text

from app.models import (
    EventoAuditoria,
    InventarioSucursal,
    LoteInventario,
    Producto,
    Venta,
    VentaDetalle,
)
from app.orders.models import PedidoOnline, ReservaPedido
from app.orders.service import movement
from app.orders.transfers import generate_order_transfers
from app.payments.client import MercadoPagoClient, MercadoPagoError
from app.payments.models import CheckoutMercadoPago, PagoMercadoPago
from app.payments.service import lock_order


class PaymentVerificationError(ValueError):
    """Los datos del proveedor no coinciden con la operación esperada."""


def instant(value):
    if not isinstance(value, str):
        raise PaymentVerificationError()
    try:
        result = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        raise PaymentVerificationError() from None
    if result.tzinfo is None:
        raise PaymentVerificationError()
    return result


def amount(value):
    try:
        result = Decimal(str(value))
    except (InvalidOperation, ValueError):
        raise PaymentVerificationError() from None
    if not result.is_finite() or result <= 0:
        raise PaymentVerificationError()
    return result


def verify_payment(data, payment_id, account):
    if (
        str(data.get("id")) != payment_id
        or data.get("currency_id") != "CLP"
        or data.get("live_mode") is not False
        or account.get("site_id") != "MLC"
        or "test_user" not in account.get("tags", [])
        or not account.get("id")
        or str(data.get("collector_id")) != str(account["id"])
    ):
        raise PaymentVerificationError()
    status = data.get("status")
    if status not in {
        "approved",
        "pending",
        "in_process",
        "authorized",
        "in_mediation",
        "rejected",
        "cancelled",
        "refunded",
        "charged_back",
    }:
        raise PaymentVerificationError()
    total = amount(data.get("transaction_amount"))
    updated = instant(data.get("date_last_updated"))
    approved = instant(data["date_approved"]) if data.get("date_approved") else None
    if status == "approved" and (approved is None or data.get("captured") is not True):
        raise PaymentVerificationError()
    if approved and approved > updated:
        raise PaymentVerificationError()
    return status, total, updated, approved


def release_reservations(db, order):
    rows = list(
        db.scalars(
            select(ReservaPedido).where(
                ReservaPedido.pedido_id == order.id,
                ReservaPedido.activa.is_(True),
            )
        )
    )
    totals = dict(
        db.execute(
            select(
                LoteInventario.inventario_sucursal_id,
                func.sum(ReservaPedido.cantidad),
            )
            .join(ReservaPedido, ReservaPedido.lote_id == LoteInventario.id)
            .where(
                ReservaPedido.pedido_id == order.id,
                ReservaPedido.activa.is_(True),
            )
            .group_by(LoteInventario.inventario_sucursal_id)
        ).all()
    )
    inventories = list(
        db.scalars(
            select(InventarioSucursal)
            .where(
                InventarioSucursal.id.in_(totals),
            )
            .order_by(InventarioSucursal.producto_id, InventarioSucursal.sucursal_id)
            .with_for_update(of=InventarioSucursal)
        )
    )
    for inv in inventories:
        quantity = totals[inv.id]
        if inv.stock_reservado < quantity:
            raise PaymentVerificationError()
        movement(db, inv, order.id, -quantity, release=True)
    for row in rows:
        row.activa = False
    order.estado = "CANCELADO"


def register_sale(db, order, approved):
    # La restricción UNIQUE(pedido_id) refuerza la exclusión por pedido.
    existing = db.scalar(select(Venta).where(Venta.pedido_id == order.id))
    if existing:
        return existing
    subtotal = sum((d.precio_base * d.cantidad for d in order.detalles), Decimal(0))
    sale = Venta(
        id=uuid4(),
        pedido_id=order.id,
        solicitud_hash=sha256(("online:" + str(order.id)).encode()).hexdigest(),
        sesion_caja_id=None,
        usuario_id=None,
        sucursal_id=order.sucursal_id,
        fecha=approved,
        medio_pago="MERCADOPAGO",
        subtotal=subtotal,
        descuento=subtotal - order.total,
        total=order.total,
    )
    db.add(sale)
    db.flush()
    for detail in order.detalles:
        product = db.get(Producto, detail.producto_id)
        db.add(
            VentaDetalle(
                venta_id=sale.id,
                producto_id=detail.producto_id,
                nombre=detail.nombre,
                sku=product.sku,
                cantidad=detail.cantidad,
                precio_base=detail.precio_base,
                precio_final=detail.precio_unitario,
                total=detail.subtotal,
                promocion={"name": detail.promocion} if detail.promocion else None,
            )
        )
    # No se crean VentaLote ni movimientos de salida: eso ocurre al retirar.
    order.estado = "PAGADO"
    return sale


class PaymentNotificationService:
    def __init__(self, factory, settings, client=None):
        self.factory = factory
        self.client = client or MercadoPagoClient(settings)

    def process(self, payment_id):
        try:
            return self._process(payment_id)
        except MercadoPagoError:
            # No reconocer una entrega que no pudimos verificar/procesar.
            raise HTTPException(
                503, "No se pudo verificar el pago. Reintenta la notificación."
            ) from None
        except (PaymentVerificationError, KeyError, TypeError):
            raise HTTPException(422, "La notificación requiere revisión.") from None

    def _process(self, payment_id):
        account = self.client.get_account()
        with self.factory.begin() as db:
            # Serializa consultas de un mismo pago para evitar aplicar respuestas
            # concurrentes en orden inverso. Todos los cambios se confirman juntos.
            db.execute(
                text("SELECT pg_advisory_xact_lock(hashtextextended(:key, 0))"),
                {"key": "mp-payment:" + payment_id},
            )
            data = self.client.get_payment(payment_id)
            status, total, updated, approved = verify_payment(data, payment_id, account)
            try:
                order_id = UUID(data.get("external_reference", ""))
            except (ValueError, TypeError, AttributeError):
                return {"received": True, "result": "unrelated"}
            lock_order(db, order_id)
            order = db.get(PedidoOnline, order_id)
            checkout = db.get(CheckoutMercadoPago, order_id)
            if order is None:
                return {"received": True, "result": "unrelated"}
            if checkout is None or checkout.estado != "LISTO":
                raise MercadoPagoError("La preferencia todavía no está confirmada.")
            if total != order.total or total != checkout.total:
                raise PaymentVerificationError()
            provider_order = data.get("order") or {}
            if provider_order.get("type") != "mercadopago":
                raise PaymentVerificationError()
            merchant_id = str(provider_order.get("id", ""))
            merchant = self.client.get_merchant_order(merchant_id)
            if (
                str(merchant.get("id")) != merchant_id
                or merchant.get("preference_id") != checkout.preferencia_id
                or merchant.get("external_reference") != str(order.id)
                or str((merchant.get("collector") or {}).get("id"))
                != str(account["id"])
                or not any(
                    str(p.get("id")) == payment_id for p in merchant.get("payments", [])
                )
            ):
                raise PaymentVerificationError()
            previous_order_state = order.estado
            row = db.get(PagoMercadoPago, payment_id)
            if row and row.pedido_id != order.id:
                raise PaymentVerificationError()
            if row and updated < row.proveedor_actualizado_en:
                return {"received": True, "result": "older"}
            if row and row.estado == status and updated == row.proveedor_actualizado_en:
                return {"received": True, "result": "duplicate"}
            if (
                row
                and row.estado in {"approved", "refunded", "charged_back"}
                and status
                in {
                    "pending",
                    "in_process",
                    "authorized",
                    "rejected",
                    "cancelled",
                }
            ):
                return {"received": True, "result": "older"}
            if row is None:
                row = PagoMercadoPago(id=payment_id, pedido_id=order.id)
                db.add(row)
            row.estado, row.total, row.moneda = status, total, "CLP"
            row.proveedor_actualizado_en = updated
            row.aprobado_en = approved
            row.procesado_en = datetime.now(timezone.utc)
            sale = db.scalar(select(Venta).where(Venta.pedido_id == order.id))
            try:
                refunded = Decimal(str(data.get("transaction_amount_refunded", 0)))
            except InvalidOperation:
                raise PaymentVerificationError() from None
            if not refunded.is_finite() or refunded < 0 or refunded > total:
                raise PaymentVerificationError()
            if refunded > 0 and status == "approved":
                row.revision_motivo = "REVISAR_REEMBOLSO_PARCIAL"
                if sale:
                    order.estado = "REVISION_PAGO"
                elif order.estado == "PENDIENTE_PAGO":
                    release_reservations(db, order)
            elif status == "approved":
                other_approved = db.scalar(
                    select(PagoMercadoPago.id).where(
                        PagoMercadoPago.pedido_id == order.id,
                        PagoMercadoPago.id != payment_id,
                        PagoMercadoPago.aprobado_en.is_not(None),
                    )
                )
                if other_approved:
                    row.revision_motivo = "SEGUNDO_PAGO_APROBADO"
                elif sale:
                    pass
                elif order.estado != "PENDIENTE_PAGO":
                    row.revision_motivo = "APROBADO_SOBRE_PEDIDO_NO_PENDIENTE"
                elif approved > checkout.vence_en or approved < order.creado_en:
                    row.revision_motivo = "APROBADO_FUERA_DE_PLAZO"
                    release_reservations(db, order)
                else:
                    reservations = dict(
                        db.execute(
                            select(
                                ReservaPedido.detalle_id,
                                func.sum(ReservaPedido.cantidad),
                            )
                            .where(
                                ReservaPedido.pedido_id == order.id,
                                ReservaPedido.activa.is_(True),
                            )
                            .group_by(ReservaPedido.detalle_id)
                        ).all()
                    )
                    if any(
                        reservations.get(d.id, 0) != d.cantidad for d in order.detalles
                    ):
                        raise PaymentVerificationError()
                    register_sale(db, order, approved)
                    generate_order_transfers(db, order)
            elif (
                status in {"rejected", "cancelled"} and order.estado == "PENDIENTE_PAGO"
            ):
                release_reservations(db, order)
            elif status in {"refunded", "charged_back", "in_mediation"}:
                row.revision_motivo = "REVISAR_REEMBOLSO_O_DISPUTA"
                if sale:
                    order.estado = "REVISION_PAGO"
                elif order.estado == "PENDIENTE_PAGO":
                    release_reservations(db, order)
            db.add(EventoAuditoria(
                origen_actor="MERCADOPAGO",
                accion="E7-H2_PAGO_VERIFICADO",
                referencia_historica=f"Pedido {order.id}",
                sucursal_id=order.sucursal_id,
                datos_cambio={
                    "pedido_id": str(order.id), "pago_id": payment_id,
                    "estado_pago": status, "anterior": previous_order_state,
                    "nuevo": order.estado, "revision_motivo": row.revision_motivo,
                },
            ))
            db.flush()
            return {
                "received": True,
                "result": "review" if row.revision_motivo else "processed",
            }
