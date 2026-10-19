from datetime import datetime, timezone
from decimal import Decimal
from hashlib import sha256
from hmac import compare_digest
from uuid import UUID

from fastapi import HTTPException
from sqlalchemy import select, text, tuple_

from app.customers.models import Cliente
from app.ecommerce.cart.service import CartService
from app.models import (
    InventarioSucursal,
    LoteInventario,
    MovimientoInventario,
    Sucursal,
)
from app.orders.models import PedidoDetalle, PedidoOnline, ReservaPedido
from app.promotions.pricing import calculate_price
from app.promotions.repository import PromotionRepository
from app.transfers.repository import TransferRepository


def summary(row):
    return {
        "id": row.id,
        "number": "WEB-" + row.id.hex.upper(),
        "created_at": row.creado_en,
        "status": row.estado,
        "total": str(row.total),
        "currency": "CLP",
        "pickup_branch": {"id": row.sucursal_id, "name": row.sucursal.nombre},
        "items": [
            {
                "product_id": d.producto_id,
                "name": d.nombre,
                "quantity": d.cantidad,
                "unit_price": str(d.precio_unitario),
                "subtotal": str(d.subtotal),
                "promotion": d.promocion,
            }
            for d in row.detalles
        ],
    }


def movement(db, inv, order_id, quantity, release=False):
    db.add(
        MovimientoInventario(
            inventario_sucursal_id=inv.id,
            usuario_id=None,
            tipo="LIBERACION_RESERVA" if release else "RESERVA",
            cantidad_fisica=0,
            cantidad_reservada=quantity,
            stock_fisico_anterior=inv.stock_fisico,
            stock_fisico_resultante=inv.stock_fisico,
            stock_reservado_anterior=inv.stock_reservado,
            stock_reservado_resultante=inv.stock_reservado + quantity,
            motivo="Reserva de pedido online"
            if not release
            else "Liberación de reserva online",
            referencia_tipo="PEDIDO_ONLINE",
            referencia_id=order_id,
        )
    )
    inv.stock_reservado += quantity


class OrderService:
    def __init__(self, factory):
        self.factory = factory

    def create(self, data, customer_id=None):
        key_hash = sha256(data.request_token.get_secret_value().encode()).hexdigest()
        fingerprint = sha256(
            data.model_dump_json(exclude={"request_token"}).encode()
        ).hexdigest()
        now = datetime.now(timezone.utc)
        with self.factory.begin() as db:
            db.execute(
                text("SELECT pg_advisory_xact_lock(hashtextextended(:key, 0))"),
                {"key": "order:" + str(data.request_id)},
            )
            existing = db.get(PedidoOnline, data.request_id)
            if existing:
                if (
                    existing.cliente_id != customer_id
                    or not compare_digest(existing.clave_hash, key_hash)
                    or existing.solicitud_hash != fingerprint
                ):
                    raise HTTPException(
                        409, "La solicitud ya fue utilizada con otros datos."
                    )
                return summary(existing), False
            if customer_id:
                customer = db.scalar(
                    select(Cliente)
                    .where(Cliente.id == customer_id)
                    .with_for_update(read=True)
                )
                if not customer or not customer.activo:
                    raise HTTPException(401, "Inicia sesión nuevamente.")
                if data.guest is not None:
                    raise HTTPException(
                        422,
                        "Con una sesión de cliente, confirma el pedido con tu cuenta.",
                    )
                name, email = customer.nombre, customer.correo
            elif data.guest:
                name, email = data.guest.name, str(data.guest.email)
            else:
                raise HTTPException(
                    422, "Ingresa nombre y correo para continuar como invitado."
                )
            branches = list(
                db.scalars(
                    select(Sucursal)
                    .where(Sucursal.activa.is_(True))
                    .order_by(Sucursal.id)
                    .with_for_update(read=True)
                )
            )
            if data.pickup_branch_id not in {b.id for b in branches}:
                raise HTTPException(
                    409, "La sucursal de retiro está inactiva o no existe."
                )
            order = PedidoOnline(
                id=data.request_id,
                solicitud_hash=fingerprint,
                clave_hash=key_hash,
                cliente_id=customer_id,
                sucursal_id=data.pickup_branch_id,
                nombre=name,
                correo=email,
                total=Decimal(0),
                creado_en=now,
                estado="PENDIENTE_PAGO",
            )
            db.add(order)
            db.flush()
            promotions = PromotionRepository.pricing(db)
            for item in sorted(data.items, key=lambda i: str(i.product_id)):
                product = TransferRepository.product(db, item.product_id)
                if (
                    not product
                    or not product.activo
                    or not product.publicado_online
                    or product.requiere_receta
                ):
                    raise HTTPException(
                        409, "Un producto no está permitido para compra online."
                    )
                inventories = list(
                    db.scalars(
                        select(InventarioSucursal)
                        .where(
                            InventarioSucursal.producto_id == product.id,
                            InventarioSucursal.sucursal_id.in_(
                                [b.id for b in branches]
                            ),
                        )
                        .order_by(InventarioSucursal.sucursal_id)
                        .with_for_update(of=InventarioSucursal)
                        .execution_options(populate_existing=True)
                    )
                )
                price = calculate_price(product, promotions, now)
                detail = PedidoDetalle(
                    pedido_id=order.id,
                    producto_id=product.id,
                    nombre=product.nombre,
                    cantidad=item.quantity,
                    precio_unitario=price["price"],
                    precio_base=price["base_price"],
                    subtotal=price["price"] * item.quantity,
                    promocion=price["promotion"].name if price["promotion"] else None,
                )
                db.add(detail)
                db.flush()
                needed = item.quantity
                for inv in sorted(
                    inventories,
                    key=lambda i: (
                        i.sucursal_id != data.pickup_branch_id,
                        str(i.sucursal_id),
                    ),
                ):
                    if needed == 0:
                        break
                    reserved = TransferRepository.reserved_lots(db, inv.id)
                    lots = TransferRepository.lots(db, inv.id, now.date())
                    all_lots = list(
                        db.scalars(
                            select(LoteInventario).where(
                                LoteInventario.inventario_sucursal_id == inv.id
                            )
                        )
                    )
                    free = CartService.available(inv, all_lots, reserved, now.date())
                    if free is None:
                        raise HTTPException(
                            409, "El inventario requiere revisión antes de reservar."
                        )
                    amount = min(needed, free)
                    remaining = amount
                    for lot in lots:
                        take = min(
                            remaining, max(0, lot.cantidad - reserved.get(lot.id, 0))
                        )
                        if take:
                            db.add(
                                ReservaPedido(
                                    pedido_id=order.id,
                                    detalle_id=detail.id,
                                    lote_id=lot.id,
                                    cantidad=take,
                                    activa=True,
                                )
                            )
                            remaining -= take
                        if remaining == 0:
                            break
                    if amount:
                        movement(db, inv, order.id, amount)
                        needed -= amount
                if needed:
                    raise HTTPException(
                        409,
                        "Ya no hay unidades vendibles suficientes. Revisa el carrito.",
                    )
                order.total += detail.subtotal
            if order.total != data.expected_total:
                raise HTTPException(
                    409, "El precio cambió. Revisa el nuevo total antes de confirmar."
                )
            db.flush()
            return summary(order), True

    def history(self, customer_id, limit=15, before=None):
        with self.factory() as db:
            query = select(PedidoOnline).where(PedidoOnline.cliente_id == customer_id)
            if before is not None:
                try:
                    timestamp, identity = before.split("|", 1)
                    point = datetime.fromisoformat(timestamp)
                    if point.tzinfo is None:
                        raise ValueError()
                    identity = UUID(identity)
                except (ValueError, AttributeError):
                    raise HTTPException(
                        422, "La página de pedidos no es válida."
                    ) from None
                query = query.where(
                    tuple_(PedidoOnline.creado_en, PedidoOnline.id)
                    < tuple_(point, identity)
                )
            rows = list(
                db.scalars(
                    query.order_by(
                        PedidoOnline.creado_en.desc(), PedidoOnline.id.desc()
                    ).limit(limit + 1)
                )
            )
            return {
                "orders": [summary(row) for row in rows[:limit]],
                "next_cursor": rows[limit - 1].creado_en.isoformat()
                + "|"
                + str(rows[limit - 1].id)
                if len(rows) > limit
                else None,
            }
