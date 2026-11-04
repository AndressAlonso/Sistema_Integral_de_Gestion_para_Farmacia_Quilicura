"""Consultas agregadas, de solo lectura; Venta es la única fuente de ventas."""
from datetime import date, timedelta
from decimal import Decimal

from sqlalchemy import func, select

from app.models import (
    InventarioSucursal,
    LoteInventario,
    MovimientoInventario,
    Producto,
    ReversaVenta,
    Sucursal,
    Venta,
    VentaDetalle,
)


def money(value):
    return str(Decimal(value or 0).quantize(Decimal("0.01")))


def dashboard(db, branch_id, start, end, since, until, today):
    branches = [
        {"id": str(row.id), "name": row.nombre}
        for row in db.execute(select(Sucursal.id, Sucursal.nombre).order_by(Sucursal.nombre))
    ]
    sale_filters = [Venta.fecha >= since, Venta.fecha < until]
    reversal_filters = [ReversaVenta.fecha >= since, ReversaVenta.fecha < until]
    inventory_filters = []
    if branch_id:
        sale_filters.append(Venta.sucursal_id == branch_id)
        reversal_filters.append(Venta.sucursal_id == branch_id)
        inventory_filters.append(InventarioSucursal.sucursal_id == branch_id)

    # No unir pagos/pedidos: una venta online ya está registrada una sola vez aquí.
    count, gross = db.execute(select(
        func.count(Venta.id), func.coalesce(func.sum(Venta.total), 0),
    ).where(*sale_filters)).one()
    returns = db.scalar(select(func.coalesce(func.sum(ReversaVenta.importe), 0))
                        .join(Venta, Venta.id == ReversaVenta.venta_id)
                        .where(*reversal_filters))

    local_day = func.date(func.timezone("America/Santiago", Venta.fecha))
    daily = {
        str(day): {"total": money(total), "count": quantity}
        for day, total, quantity in db.execute(select(
            local_day, func.sum(Venta.total), func.count(Venta.id),
        ).where(*sale_filters).group_by(local_day))
    }
    timeline = []
    for offset in range((end - start).days + 1):
        day = (start + timedelta(days=offset)).isoformat()
        timeline.append({"date": day, **daily.get(day, {"total": "0.00", "count": 0})})

    payments = [
        {"method": method, "total": money(total), "count": quantity}
        for method, total, quantity in db.execute(select(
            Venta.medio_pago, func.sum(Venta.total), func.count(Venta.id),
        ).where(*sale_filters).group_by(Venta.medio_pago).order_by(func.sum(Venta.total).desc(), Venta.medio_pago))
    ]
    by_branch = [
        {"id": str(row.id), "name": row.nombre, "total": money(row.total), "count": row.quantity}
        for row in db.execute(select(
            Sucursal.id, Sucursal.nombre, func.sum(Venta.total).label("total"),
            func.count(Venta.id).label("quantity"),
        ).join(Venta, Venta.sucursal_id == Sucursal.id).where(*sale_filters)
            .group_by(Sucursal.id, Sucursal.nombre).order_by(func.sum(Venta.total).desc(), Sucursal.nombre))
    ]
    top_products = [
        {"id": str(row.producto_id), "name": row.nombre, "quantity": row.quantity}
        for row in db.execute(select(
            VentaDetalle.producto_id, Producto.nombre,
            func.sum(VentaDetalle.cantidad).label("quantity"),
        ).join(Venta, Venta.id == VentaDetalle.venta_id)
            .join(Producto, Producto.id == VentaDetalle.producto_id)
            .where(*sale_filters).group_by(VentaDetalle.producto_id, Producto.nombre)
            .order_by(func.sum(VentaDetalle.cantidad).desc(), Producto.nombre, VentaDetalle.producto_id).limit(5))
    ]

    available = InventarioSucursal.stock_fisico - InventarioSucursal.stock_reservado
    low_filters = [*inventory_filters, Producto.activo.is_(True),
                   available <= InventarioSucursal.stock_minimo]
    low_query = select(InventarioSucursal.id).join(
        Producto, Producto.id == InventarioSucursal.producto_id,
    ).where(*low_filters)
    low_count = db.scalar(select(func.count()).select_from(low_query.subquery()))
    low_stock = [
        {"id": str(row.id), "name": row.nombre, "branch": row.branch,
         "available": row.available, "minimum": row.stock_minimo}
        for row in db.execute(select(
            InventarioSucursal.id, Producto.nombre, Sucursal.nombre.label("branch"),
            available.label("available"), InventarioSucursal.stock_minimo,
        ).join(Producto, Producto.id == InventarioSucursal.producto_id)
            .join(Sucursal, Sucursal.id == InventarioSucursal.sucursal_id)
            .where(*low_filters).order_by(available, Producto.nombre, Sucursal.nombre).limit(5))
    ]
    lot_filters = [*inventory_filters, LoteInventario.activo.is_(True),
                   LoteInventario.cantidad > 0]
    lots = select(
        LoteInventario.id, LoteInventario.numero_lote, LoteInventario.fecha_vencimiento,
        LoteInventario.cantidad, Producto.nombre, Sucursal.nombre.label("branch"),
    ).join(InventarioSucursal, InventarioSucursal.id == LoteInventario.inventario_sucursal_id
           ).join(Producto, Producto.id == InventarioSucursal.producto_id
                  ).join(Sucursal, Sucursal.id == InventarioSucursal.sucursal_id)
    upcoming_filters = [
        *lot_filters, LoteInventario.fecha_vencimiento > today,
        LoteInventario.fecha_vencimiento <= today + timedelta(days=30),
    ]
    expiring_count = db.scalar(select(func.count()).select_from(lots.where(*upcoming_filters).subquery()))
    expired_count = db.scalar(select(func.count()).select_from(lots.where(
        *lot_filters, LoteInventario.fecha_vencimiento <= today,
    ).subquery()))
    expiring = []
    for row in db.execute(lots.where(*upcoming_filters).order_by(
        LoteInventario.fecha_vencimiento, Producto.nombre, Sucursal.nombre, LoteInventario.id,
    ).limit(5)):
        expiry = row.fecha_vencimiento
        if isinstance(expiry, str):
            expiry = date.fromisoformat(expiry)
        expiring.append({
            "id": str(row.id), "name": row.nombre, "branch": row.branch,
            "lot": row.numero_lote, "date": expiry.isoformat(), "quantity": row.cantidad,
            "days": (expiry - today).days,
        })
    movements = [
        {"type": row.tipo, "count": row.quantity, "physical": row.physical, "reserved": row.reserved}
        for row in db.execute(select(
            MovimientoInventario.tipo, func.count().label("quantity"),
            func.sum(MovimientoInventario.cantidad_fisica).label("physical"),
            func.sum(MovimientoInventario.cantidad_reservada).label("reserved"),
        ).join(InventarioSucursal, InventarioSucursal.id == MovimientoInventario.inventario_sucursal_id)
            .where(*inventory_filters, MovimientoInventario.creado_en >= since,
                   MovimientoInventario.creado_en < until).group_by(MovimientoInventario.tipo)
            .order_by(func.count().desc(), MovimientoInventario.tipo))
    ]
    return {
        "branches": branches,
        "period": {"date_from": start.isoformat(), "date_to": end.isoformat()},
        "sales": {"total": money(gross), "count": count,
                  "average": money(gross / count if count else 0),
                  "returns": money(returns), "net": money(gross - returns)},
        "daily": timeline, "payments": payments, "by_branch": by_branch,
        "top_products": top_products, "movements": movements,
        "inventory": {"as_of": today.isoformat(), "low_count": low_count,
                      "expiring_count": expiring_count, "expired_count": expired_count,
                      "low_stock": low_stock, "expiring": expiring},
    }
