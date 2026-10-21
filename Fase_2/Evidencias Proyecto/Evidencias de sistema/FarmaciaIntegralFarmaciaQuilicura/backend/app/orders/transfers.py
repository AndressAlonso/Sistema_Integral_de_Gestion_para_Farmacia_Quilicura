"""E7-H3: traslados de reservas de pedido, sin duplicar existencias comprometidas."""
from collections import defaultdict
from datetime import datetime, timezone
from hashlib import sha256
from uuid import uuid4

from fastapi import HTTPException
from sqlalchemy import select, text

from app.models import (
    InventarioSucursal,
    LoteInventario,
    Transferencia,
    TransferenciaDetalle,
    TransferenciaLote,
)
from app.orders.models import PedidoOnline, ReservaPedido
from app.orders.service import movement
from app.transfers.repository import TransferRepository
from app.transfers.service import TransferService


def lock_order(db, order_id):
    # Compartido con creación/recuperación del pedido y todas sus transferencias.
    db.execute(text("SELECT pg_advisory_xact_lock(hashtextextended(:key, 0))"),
               {"key": "order:" + str(order_id)})
    order = db.scalar(select(PedidoOnline).where(PedidoOnline.id == order_id)
                      .with_for_update().execution_options(populate_existing=True))
    if order is None:
        raise HTTPException(404, "El pedido no existe.")
    return order


def reservation_rows(db, order_id):
    return list(db.execute(select(ReservaPedido, LoteInventario, InventarioSucursal)
                           .join(LoteInventario, LoteInventario.id == ReservaPedido.lote_id)
                           .join(InventarioSucursal, InventarioSucursal.id == LoteInventario.inventario_sucursal_id)
                           .where(ReservaPedido.pedido_id == order_id, ReservaPedido.activa.is_(True))
                           .order_by(InventarioSucursal.producto_id, InventarioSucursal.sucursal_id, ReservaPedido.id)))


def generate_order_transfers(db, order):
    """Llamar dentro de la transacción de pago confirmado, con el pedido bloqueado."""
    if order.estado != "PAGADO":
        raise HTTPException(409, "El pedido debe estar pagado para generar traslados.")
    existing = list(db.scalars(select(Transferencia).where(Transferencia.pedido_id == order.id)))
    if existing:
        return existing
    rows = reservation_rows(db, order.id)
    totals = defaultdict(int)
    for reservation, _, inv in rows:
        totals[inv.producto_id] += reservation.cantidad
    if dict(totals) != {d.producto_id: d.cantidad for d in order.detalles}:
        raise HTTPException(409, "Las reservas no cubren el pedido; requiere revisión.")
    branch_ids = {order.sucursal_id, *(inv.sucursal_id for _, _, inv in rows)}
    branches = TransferRepository.branches(db, branch_ids)
    if len(branches) != len(branch_ids) or not all(b.activa for b in branches):
        raise HTTPException(409, "Una sucursal del pedido está inactiva.")
    now = datetime.now(timezone.utc)
    transfers, details = {}, {}
    for reservation, lot, inventory in rows:
        product = TransferRepository.product(db, inventory.producto_id)
        inv = TransferRepository.inventory(db, inventory.producto_id, inventory.sucursal_id)
        # Otra operación puede cambiar el lote mientras esperamos el bloqueo del inventario.
        db.refresh(lot)
        reserved = TransferRepository.reserved_lots(db, inv.id)
        if (not product.activo or not lot.activo or lot.fecha_vencimiento <= now.date()
                or inv.stock_reservado > inv.stock_fisico
                or inv.stock_reservado < reservation.cantidad
                or lot.cantidad < reserved.get(lot.id, 0)):
            raise HTTPException(409, "Una reserva ya no es vendible; revisa el pedido.")
        if inv.sucursal_id == order.sucursal_id:
            continue
        TransferService.validate_destination(db, product, order.sucursal_id, lot)
        row = transfers.get(inv.sucursal_id)
        if row is None:
            row = Transferencia(id=uuid4(), pedido_id=order.id,
                                solicitud_hash=sha256(f"order:{order.id}:{inv.sucursal_id}".encode()).hexdigest(),
                                origen_id=inv.sucursal_id, destino_id=order.sucursal_id,
                                estado="AUTORIZADA", solicitante_id=None,
                                solicitada_en=now, autorizada_en=now)
            transfers[inv.sucursal_id] = row
            db.add(row)
            db.flush()
        key = (inv.sucursal_id, inv.producto_id)
        detail = details.get(key)
        if detail is None:
            detail = TransferenciaDetalle(transferencia_id=row.id, producto_id=inv.producto_id, cantidad=reservation.cantidad)
            details[key] = detail
            db.add(detail)
            db.flush()
        else:
            detail.cantidad += reservation.cantidad
        db.add(TransferenciaLote(detalle_id=detail.id, lote_origen_id=lot.id,
                                cantidad=reservation.cantidad, reserva_pedido_id=reservation.id))
    db.flush()
    return list(transfers.values())


def release_order_reservations(db, order):
    for reservation, _, inventory in reservation_rows(db, order.id):
        inv = TransferRepository.inventory(db, inventory.producto_id, inventory.sucursal_id)
        if inv.stock_reservado < reservation.cantidad:
            raise HTTPException(409, "La reserva no coincide con el inventario.")
        movement(db, inv, order.id, -reservation.cantidad, release=True)
        reservation.activa = False

