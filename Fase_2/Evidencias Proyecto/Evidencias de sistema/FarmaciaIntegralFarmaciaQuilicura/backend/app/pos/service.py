import hashlib
import json
from datetime import datetime, timezone
from decimal import Decimal
from uuid import UUID

from sqlalchemy import String, cast, func, or_, select

from app.models import (
    CodigoBarra,
    LoteInventario,
    MovimientoInventario,
    Producto,
    ReversaVenta,
    ReversaVentaDetalle,
    SesionCaja,
    Sucursal,
    UsuarioInterno,
    Venta,
    VentaDetalle,
    VentaLote,
)
from app.pos.pricing import best_price, money
from app.transfers.repository import TransferRepository

PAYMENTS = ("EFECTIVO", "DEBITO", "CREDITO", "TRANSFERENCIA")


def version(value):
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, default=str, separators=(",", ":")).encode()
    ).hexdigest()


class PosError(Exception):
    def __init__(self, status, message):
        self.status, self.message = status, message


class PosService:
    def __init__(self, repository, promotions=()):
        self.repo = repository
        self.promotions = promotions

    @staticmethod
    def authorize(actor, permission):
        if permission not in actor.permissions:
            raise PosError(403, "No tienes permiso para operar este módulo.")

    @staticmethod
    def branch(db, actor):
        branches = TransferRepository.branches(db, [actor.branch_id])
        if not branches or not branches[0].activa:
            raise PosError(409, "Tu sucursal no está activa.")
        return branches[0]

    @staticmethod
    def availability(db, product_id, branch_id):
        inventory = TransferRepository.inventory(db, product_id, branch_id)
        if inventory is None:
            return None, [], 0
        today = datetime.now(timezone.utc).date()
        lots = TransferRepository.lots(db, inventory.id, today)
        reserved = TransferRepository.reserved_lots(db, inventory.id)
        allocations = [
            (lot, max(0, lot.cantidad - reserved.get(lot.id, 0))) for lot in lots
        ]
        available = max(
            0, min(inventory.stock_disponible, sum(qty for _, qty in allocations))
        )
        return inventory, allocations, available

    def product_image_key(self, actor, product_id):
        self.authorize(actor, "pos.operar")
        with self.repo.factory.begin() as db:
            self.branch(db, actor)
            product = db.get(Producto, product_id)
            if product is None or not product.activo:
                raise PosError(404, "Imagen no disponible.")
            return product.image_key

    def products(self, actor, query):
        self.authorize(actor, "pos.operar")
        with self.repo.factory.begin() as db:
            self.branch(db, actor)
            pattern = f"%{query.replace('%', '').replace('_', '')}%"
            rows = db.scalars(
                select(Producto)
                .where(
                    Producto.activo.is_(True),
                    or_(
                        Producto.nombre.ilike(pattern),
                        Producto.sku.ilike(pattern),
                        cast(Producto.id, String) == query,
                        Producto.id.in_(
                            select(CodigoBarra.producto_id).where(
                                CodigoBarra.valor == query
                            )
                        ),
                    ),
                )
                .order_by(Producto.id)
                .limit(50)
            ).all()
            result = []
            for product in rows:
                _, _, available = self.availability(db, product.id, actor.branch_id)
                result.append(
                    {
                        "id": str(product.id),
                        "name": product.nombre,
                        "sku": product.sku,
                        "price": str(product.precio_actual),
                        "available": available,
                        "requires_prescription": product.requiere_receta,
                    }
                )
            return {"products": result}

    def calculate(self, db, actor, items):
        lines, stock = [], {}
        for item in sorted(items, key=lambda row: str(row.product_id)):
            product = TransferRepository.product(db, item.product_id)
            if product is None or not product.activo:
                raise PosError(
                    409, "Un producto ya no está disponible. Revisa el carrito."
                )
            inventory, allocations, available = self.availability(
                db, product.id, actor.branch_id
            )
            if item.quantity > available:
                raise PosError(
                    409,
                    f"Stock vendible insuficiente para {product.nombre}: quedan {available}.",
                )
            price, promotion = best_price(
                product.precio_actual,
                product.id,
                product.categoria_id,
                datetime.now(timezone.utc),
                self.promotions,
            )
            lines.append(
                {
                    "product_id": str(product.id),
                    "name": product.nombre,
                    "sku": product.sku,
                    "quantity": item.quantity,
                    "base_price": str(product.precio_actual),
                    "price": str(price),
                    "promotion": promotion,
                    "total": str(money(price * item.quantity)),
                }
            )
            stock[product.id] = (inventory, allocations)
        subtotal = sum(
            (Decimal(line["base_price"]) * line["quantity"] for line in lines),
            Decimal(0),
        )
        total = sum((Decimal(line["total"]) for line in lines), Decimal(0))
        if subtotal >= Decimal(1000000000000):
            raise PosError(422, "El importe del carrito supera el límite permitido.")
        quote = {
            "items": lines,
            "subtotal": str(money(subtotal)),
            "discount": str(money(subtotal - total)),
            "total": str(money(total)),
        }
        quote["version"] = version({"branch": actor.branch_id, **quote})
        return quote, stock

    def quote(self, actor, data):
        self.authorize(actor, "pos.operar")
        with self.repo.factory.begin() as db:
            self.branch(db, actor)
            return self.calculate(db, actor, data.items)[0]

    @staticmethod
    def cash_response(cash):
        if cash is None:
            return None
        return {
            "id": str(cash.id),
            "opened_at": cash.apertura_en.isoformat(),
            "initial_amount": str(cash.monto_inicial),
            "closed_at": cash.cierre_en.isoformat() if cash.cierre_en else None,
            "summary": cash.resumen_cierre,
        }

    def current(self, actor):
        self.authorize(actor, "caja.operar")
        with self.repo.factory.begin() as db:
            return self.cash_response(self.repo.current_cash(db, actor))

    def open(self, actor, data):
        self.authorize(actor, "caja.operar")
        with self.repo.factory.begin() as db:
            self.branch(db, actor)
            self.repo.lock(db, f"cash:{actor.id}:{actor.branch_id}")
            existing = db.get(SesionCaja, data.request_id)
            if existing:
                if (
                    existing.usuario_id != actor.id
                    or existing.sucursal_id != actor.branch_id
                    or existing.monto_inicial != data.initial_amount
                ):
                    raise PosError(
                        409, "El identificador de apertura ya fue utilizado."
                    )
                return self.cash_response(existing)
            if self.repo.current_cash(db, actor):
                raise PosError(409, "Ya tienes una caja abierta en esta sucursal.")
            cash = SesionCaja(
                id=data.request_id,
                usuario_id=actor.id,
                sucursal_id=actor.branch_id,
                monto_inicial=data.initial_amount,
            )
            db.add(cash)
            db.flush()
            return self.cash_response(cash)

    def cash(self, db, actor, cash_id):
        cash = db.scalar(
            select(SesionCaja).where(SesionCaja.id == cash_id).with_for_update()
        )
        if (
            cash is None
            or cash.usuario_id != actor.id
            or cash.sucursal_id != actor.branch_id
        ):
            raise PosError(404, "No encontramos esa caja en tu sesión de trabajo.")
        return cash

    def summary_data(self, db, cash):
        sales = self.repo.sales(db, cash.id)
        totals = {
            payment: sum(
                (sale.total for sale in sales if sale.medio_pago == payment), Decimal(0)
            )
            for payment in PAYMENTS
        }
        total = sum(totals.values(), Decimal(0))
        refunds = {payment: Decimal(0) for payment in PAYMENTS}
        reversals = db.execute(
            select(ReversaVenta, Venta.medio_pago)
            .join(Venta, Venta.id == ReversaVenta.venta_id)
            .where(ReversaVenta.sesion_caja_id == cash.id)
            .order_by(ReversaVenta.id)
        ).all()
        for reversal, payment in reversals:
            refunds[payment] += reversal.importe
        result = {
            "payments": {key: str(money(amount)) for key, amount in totals.items()},
            "refunds": {key: str(money(amount)) for key, amount in refunds.items()},
            "sales_count": len(sales),
            "total": str(money(total)),
            "average_ticket": str(money(total / len(sales))) if sales else "0.00",
            "expected_cash": str(
                money(cash.monto_inicial + totals["EFECTIVO"] - refunds["EFECTIVO"])
            ),
        }
        result["version"] = version(
            {
                "cash": cash.id,
                "sales": [sale.id for sale in sales],
                "reversals": [row.id for row, _ in reversals],
                **result,
            }
        )
        return result

    def summary(self, actor, cash_id):
        self.authorize(actor, "caja.operar")
        with self.repo.factory.begin() as db:
            cash = self.cash(db, actor, cash_id)
            return cash.resumen_cierre or self.summary_data(db, cash)

    def close(self, actor, cash_id, data):
        self.authorize(actor, "caja.operar")
        with self.repo.factory.begin() as db:
            cash = self.cash(db, actor, cash_id)
            if cash.cierre_en:
                if (
                    cash.efectivo_contado != data.counted_cash
                    or cash.resumen_cierre["version"] != data.summary_version
                ):
                    raise PosError(409, "La caja ya se cerró con otros datos.")
                return self.cash_response(cash)
            summary = self.summary_data(db, cash)
            if summary["version"] != data.summary_version:
                raise PosError(
                    409,
                    "Se registraron nuevas ventas. Actualiza el resumen antes de cerrar.",
                )
            summary["counted_cash"] = str(data.counted_cash)
            summary["difference"] = str(
                money(data.counted_cash - Decimal(summary["expected_cash"]))
            )
            cash.cierre_en = datetime.now(timezone.utc)
            cash.efectivo_contado = data.counted_cash
            cash.resumen_cierre = summary
            db.flush()
            return self.cash_response(cash)

    def sell(self, actor, data):
        with self.repo.factory.begin() as db:
            self.authorize(actor, "pos.operar")
            self.authorize(actor, "caja.operar")
            request_hash = version(data.model_dump(mode="json"))
            self.repo.lock(db, f"sale:{data.request_id}")
            existing = db.get(Venta, data.request_id)
            if existing:
                if (
                    existing.usuario_id != actor.id
                    or existing.sucursal_id != actor.branch_id
                    or existing.solicitud_hash != request_hash
                ):
                    raise PosError(
                        409, "La solicitud ya fue utilizada para otra venta."
                    )
                return self.receipt_data(db, existing)
            if data.payment == "TRANSFERENCIA":
                raise PosError(422, "Selecciona efectivo o tarjeta (débito/crédito).")
            self.branch(db, actor)
            cash = self.repo.current_cash(db, actor)
            if cash is None:
                raise PosError(409, "Abre tu caja antes de finalizar una venta.")
            quote, stock = self.calculate(db, actor, data.items)
            if quote["version"] != data.quote_version:
                raise PosError(
                    409,
                    "Los precios o promociones cambiaron. Revisa nuevamente el total.",
                )
            sale = Venta(
                id=data.request_id,
                solicitud_hash=request_hash,
                sesion_caja_id=cash.id,
                usuario_id=actor.id,
                sucursal_id=actor.branch_id,
                medio_pago=data.payment,
                subtotal=Decimal(quote["subtotal"]),
                descuento=Decimal(quote["discount"]),
                total=Decimal(quote["total"]),
            )
            db.add(sale)
            db.flush()
            for line in quote["items"]:
                product_id = UUID(line["product_id"])
                detail = VentaDetalle(
                    venta_id=sale.id,
                    producto_id=product_id,
                    nombre=line["name"],
                    sku=line["sku"],
                    cantidad=line["quantity"],
                    precio_base=Decimal(line["base_price"]),
                    precio_final=Decimal(line["price"]),
                    promocion=line["promotion"],
                    total=Decimal(line["total"]),
                )
                db.add(detail)
                db.flush()
                inventory, lots = stock[product_id]
                remaining = detail.cantidad
                for lot, available in lots:
                    take = min(remaining, available)
                    if take:
                        lot.cantidad -= take
                        db.add(
                            VentaLote(
                                venta_detalle_id=detail.id,
                                lote_id=lot.id,
                                cantidad=take,
                            )
                        )
                        remaining -= take
                    if not remaining:
                        break
                if remaining:
                    raise PosError(409, "No se pudo completar la asignación de lotes.")
                before = inventory.stock_fisico
                inventory.stock_fisico -= detail.cantidad
                db.add(
                    MovimientoInventario(
                        inventario_sucursal_id=inventory.id,
                        usuario_id=actor.id,
                        tipo="VENTA",
                        cantidad_fisica=-detail.cantidad,
                        cantidad_reservada=0,
                        stock_fisico_anterior=before,
                        stock_fisico_resultante=inventory.stock_fisico,
                        stock_reservado_anterior=inventory.stock_reservado,
                        stock_reservado_resultante=inventory.stock_reservado,
                        motivo="Salida por venta POS",
                        referencia_tipo="VENTA",
                        referencia_id=sale.id,
                    )
                )
            db.flush()
            return self.receipt_data(db, sale)

    def receipt_data(self, db, sale):
        branch = db.get(Sucursal, sale.sucursal_id)
        user = db.get(UsuarioInterno, sale.usuario_id)
        return {
            "id": str(sale.id),
            "date": sale.fecha.isoformat(),
            "branch": branch.nombre,
            "cashier": user.nombre,
            "payment": sale.medio_pago,
            "subtotal": str(sale.subtotal),
            "discount": str(sale.descuento),
            "total": str(sale.total),
            "notice": "COMPROBANTE INTERNO SIN VALIDEZ TRIBUTARIA",
            "items": [
                {
                    "product_id": str(row.producto_id),
                    "name": row.nombre,
                    "sku": row.sku,
                    "quantity": row.cantidad,
                    "base_price": str(row.precio_base),
                    "price": str(row.precio_final),
                    "promotion": row.promocion,
                    "total": str(row.total),
                    "lots": self.sold_lots(db, row.id),
                }
                for row in self.repo.details(db, sale.id)
            ],
        }

    def receipt(self, actor, sale_id):
        self.authorize(actor, "pos.operar")
        with self.repo.factory.begin() as db:
            sale = db.get(Venta, sale_id)
            if sale is None or (
                "ADMINISTRADOR" not in actor.roles
                and (sale.usuario_id != actor.id or sale.sucursal_id != actor.branch_id)
            ):
                raise PosError(404, "No encontramos esa venta.")
            return self.receipt_data(db, sale)

    @staticmethod
    def sold_lots(db, detail_id):
        result = []
        for allocation, lot in db.execute(
            select(VentaLote, LoteInventario)
            .join(LoteInventario, LoteInventario.id == VentaLote.lote_id)
            .where(VentaLote.venta_detalle_id == detail_id)
            .order_by(VentaLote.id)
        ):
            returned = db.scalar(
                select(func.coalesce(func.sum(ReversaVentaDetalle.cantidad), 0)).where(
                    ReversaVentaDetalle.venta_lote_id == allocation.id
                )
            )
            result.append(
                {
                    "sale_lot_id": str(allocation.id),
                    "number": lot.numero_lote,
                    "expires_at": lot.fecha_vencimiento.isoformat(),
                    "quantity": allocation.cantidad,
                    "returnable": allocation.cantidad - returned,
                }
            )
        return result

    def list_sales(self, actor):
        self.authorize(actor, "pos.operar")
        with self.repo.factory.begin() as db:
            query = select(Venta).order_by(Venta.fecha.desc(), Venta.id).limit(50)
            if "ADMINISTRADOR" not in actor.roles:
                query = query.where(
                    Venta.usuario_id == actor.id, Venta.sucursal_id == actor.branch_id
                )
            return {
                "sales": [
                    {
                        "id": str(row.id),
                        "date": row.fecha.isoformat(),
                        "total": str(row.total),
                        "payment": row.medio_pago,
                    }
                    for row in db.scalars(query)
                ]
            }

    def reverse(self, actor, sale_id, data):
        self.authorize(actor, "ventas.reversar")
        self.authorize(actor, "caja.operar")
        if "ADMINISTRADOR" not in actor.roles:
            raise PosError(
                403, "Solo un administrador puede registrar devoluciones o anulaciones."
            )
        request_hash = version({"sale": sale_id, **data.model_dump(mode="json")})
        with self.repo.factory.begin() as db:
            self.repo.lock(db, f"reversal:{data.request_id}")
            existing = db.get(ReversaVenta, data.request_id)
            if existing:
                if (
                    existing.usuario_id != actor.id
                    or existing.solicitud_hash != request_hash
                ):
                    raise PosError(
                        409, "La solicitud de devolución ya se utilizó con otros datos."
                    )
                return {"id": str(existing.id), "amount": str(existing.importe)}
            sale = db.scalar(select(Venta).where(Venta.id == sale_id).with_for_update())
            if sale is None:
                raise PosError(404, "No encontramos la venta original.")
            branches = TransferRepository.branches(
                db, sorted({actor.branch_id, sale.sucursal_id})
            )
            if not all(branch.activa for branch in branches):
                raise PosError(409, "Las sucursales involucradas deben estar activas.")
            cash = self.repo.current_cash(db, actor)
            if cash is None:
                raise PosError(409, "Abre tu caja para registrar el reembolso.")
            details = {row.id: row for row in self.repo.details(db, sale.id)}
            allocations = {
                row.id: row
                for row in db.scalars(
                    select(VentaLote).where(VentaLote.venta_detalle_id.in_(details))
                )
            }
            returned = dict(
                db.execute(
                    select(
                        ReversaVentaDetalle.venta_lote_id,
                        func.sum(ReversaVentaDetalle.cantidad),
                    )
                    .where(ReversaVentaDetalle.venta_lote_id.in_(allocations))
                    .group_by(ReversaVentaDetalle.venta_lote_id)
                ).all()
            )
            if data.kind == "ANULACION" and (
                any(returned.values())
                or {item.sale_lot_id: item.quantity for item in data.items}
                != {key: row.cantidad for key, row in allocations.items()}
            ):
                raise PosError(
                    409,
                    "La anulación requiere la venta completa y sin devoluciones previas.",
                )
            amount = Decimal(0)
            for item in data.items:
                allocation = allocations.get(item.sale_lot_id)
                if (
                    allocation is None
                    or details[allocation.venta_detalle_id].producto_id
                    != item.product_id
                ):
                    raise PosError(422, "El producto o lote no pertenece a la venta.")
                if item.quantity > allocation.cantidad - returned.get(allocation.id, 0):
                    raise PosError(
                        409, "La cantidad supera las unidades pendientes de devolución."
                    )
                amount += (
                    details[allocation.venta_detalle_id].precio_final * item.quantity
                )
            if sale.medio_pago == "EFECTIVO" and amount > Decimal(
                self.summary_data(db, cash)["expected_cash"]
            ):
                raise PosError(
                    409,
                    "La caja actual no dispone de efectivo suficiente para este reembolso.",
                )
            reversal = ReversaVenta(
                id=data.request_id,
                solicitud_hash=request_hash,
                venta_id=sale.id,
                usuario_id=actor.id,
                sesion_caja_id=cash.id,
                tipo=data.kind,
                motivo=data.reason.strip(),
                importe=money(amount),
            )
            db.add(reversal)
            db.flush()
            for item in sorted(
                data.items, key=lambda row: (str(row.product_id), str(row.sale_lot_id))
            ):
                allocation = allocations[item.sale_lot_id]
                if item.restock:
                    product = TransferRepository.product(db, item.product_id)
                    inventory = TransferRepository.inventory(
                        db, item.product_id, sale.sucursal_id
                    )
                    lot = db.get(LoteInventario, allocation.lote_id)
                    if (
                        not product.activo
                        or not lot.activo
                        or lot.fecha_vencimiento
                        <= datetime.now(timezone.utc).date()
                    ):
                        raise PosError(
                            409,
                            "Un producto inactivo o lote vencido/inactivo no puede volver al stock vendible.",
                        )
                    before = inventory.stock_fisico
                    inventory.stock_fisico += item.quantity
                    lot.cantidad += item.quantity
                    db.add(
                        MovimientoInventario(
                            inventario_sucursal_id=inventory.id,
                            usuario_id=actor.id,
                            tipo="DEVOLUCION_VENTA",
                            cantidad_fisica=item.quantity,
                            cantidad_reservada=0,
                            stock_fisico_anterior=before,
                            stock_fisico_resultante=inventory.stock_fisico,
                            stock_reservado_anterior=inventory.stock_reservado,
                            stock_reservado_resultante=inventory.stock_reservado,
                            motivo=data.reason.strip(),
                            referencia_tipo="REVERSA_VENTA",
                            referencia_id=reversal.id,
                        )
                    )
                db.add(
                    ReversaVentaDetalle(
                        reversa_id=reversal.id,
                        venta_lote_id=allocation.id,
                        cantidad=item.quantity,
                        reintegrar_stock=item.restock,
                        motivo_condicion=item.condition.strip(),
                    )
                )
            db.flush()
            return {"id": str(reversal.id), "amount": str(reversal.importe)}
