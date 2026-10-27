"""Registro de cambios ORM confirmados; sin serializar entidades completas ni secretos."""
from contextvars import ContextVar
from datetime import date, datetime
from decimal import Decimal
from uuid import UUID, uuid4

from sqlalchemy import inspect

from app.models import EventoAuditoria, InventarioSucursal, Sucursal

# Un objeto por solicitud, compartido con las dependencias síncronas de FastAPI.
request_audit: ContextVar[dict | None] = ContextVar("request_audit", default=None)

FIELDS = {
    "usuario_interno": ("nombre", "correo", "activo", "sucursal_id", "roles"),
    "rol": ("codigo", "nombre", "permisos"),
    "sucursal": ("codigo", "nombre", "direccion_local", "activa"),
    "categoria": ("nombre",),
    "producto": ("sku", "nombre", "descripcion", "categoria_id", "activo", "requiere_receta", "image_key", "publicado_online"),
    "codigo_barra": ("valor", "producto_id"),
    "movimiento_inventario": ("tipo", "cantidad_fisica", "cantidad_reservada", "stock_fisico_anterior", "stock_fisico_resultante", "stock_reservado_anterior", "stock_reservado_resultante", "motivo", "referencia_tipo", "referencia_id"),
    "inventario_sucursal": ("stock_minimo",),
    "recepcion_mercaderia": ("proveedor", "tipo_documento", "numero_documento", "fecha_documento", "sucursal_id"),
    "ajuste_inventario": ("motivo", "sucursal_id"),
    "transferencia": ("origen_id", "destino_id", "estado", "pedido_id", "motivo_rechazo"),
    "sesion_caja": ("sucursal_id", "monto_inicial", "cierre_en", "efectivo_contado"),
    "venta": ("sucursal_id", "medio_pago", "subtotal", "descuento", "total"),
    "reversa_venta": ("venta_id", "sesion_caja_id", "tipo", "motivo", "importe"),
}


def value(item):
    if isinstance(item, (datetime, date)):
        return item.isoformat()
    if isinstance(item, (UUID, Decimal)):
        return str(item)
    if isinstance(item, (list, tuple)):
        return sorted(str(getattr(entry, "codigo", entry)) for entry in item)
    return item


def record_changes(db, flush_context, instances):
    context = request_audit.get()
    if not context or not context.get("actor") or context["method"] not in {"POST", "PATCH", "PUT", "DELETE"}:
        return
    actor = context["actor"]
    for row in list(db.new) + list(db.dirty) + list(db.deleted):
        if isinstance(row, EventoAuditoria) and row in db.new:
            data = dict(row.datos_cambio)
            if row.usuario_id == actor.id:
                data.setdefault("usuario_nombre", data.get("user_name") or actor.name)
            if row.sucursal_id:
                branch = db.get(Sucursal, row.sucursal_id)
                data.setdefault("sucursal_nombre", branch.nombre if branch else None)
            row.datos_cambio = data
            continue
        table = getattr(row, "__tablename__", "")
        if table not in FIELDS:
            continue
        created, deleted = row in db.new, row in db.deleted
        state = inspect(row)
        changes = {}
        for field in FIELDS[table]:
            if field not in state.attrs:
                continue
            history = state.attrs[field].history
            branch_relationship = field == "sucursal_id" and "sucursal" in state.attrs and state.attrs.sucursal.history.has_changes()
            if branch_relationship:
                history = state.attrs.sucursal.history
            if not created and not deleted and not history.has_changes():
                continue
            current = value(getattr(row, field))
            previous = value(list(history.deleted)) if field in {"roles", "permisos"} else value(history.deleted[0]) if history.deleted else None
            if branch_relationship:
                current = str(row.sucursal.id) if row.sucursal else None
                previous = str(history.deleted[0].id) if history.deleted else None
            if field in {"roles", "permisos"} and not created and not deleted:
                previous = sorted(set(current) - set(value(list(history.added))) | set(previous))
            changes[field] = {"anterior": None if created else current if deleted else previous,
                              "nuevo": None if deleted else current}
        if not changes:
            continue
        if row.id is None:
            row.id = uuid4()
        branch_id = getattr(row, "sucursal_id", None)
        if table == "usuario_interno" and row.sucursal is not None:
            branch_id = row.sucursal.id
        if table == "sucursal":
            branch_id = row.id
        elif table == "transferencia":
            branch_id = row.origen_id
        elif table == "reversa_venta":
            branch_id = actor.branch_id
        elif table == "movimiento_inventario":
            inventory = db.get(InventarioSucursal, row.inventario_sucursal_id)
            branch_id = inventory.sucursal_id if inventory else None
        branch = row if table == "sucursal" else db.get(Sucursal, branch_id) if branch_id else None
        destination = db.get(Sucursal, row.destino_id) if table == "transferencia" else None
        operation = "creado" if created else "eliminado" if deleted else "actualizado"
        label = getattr(row, "nombre", None) or getattr(row, "codigo", None) or str(row.id)
        db.add(EventoAuditoria(
            usuario_id=actor.id, origen_actor="USUARIO_INTERNO",
            accion=f"{table}.{operation}", referencia_historica=f"{table}: {label}",
            datos_cambio={"usuario_nombre": actor.name, "entidad_id": str(row.id),
                          "sucursal_id": str(branch_id) if branch_id else None,
                          "sucursal_nombre": branch.nombre if branch else None,
                          "destino_id": str(row.destino_id) if table == "transferencia" else None,
                          "destino_nombre": destination.nombre if destination else None,
                          "cambios": changes},
        ))
