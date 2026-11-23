"""Consulta de auditoría: solo lectura, Administrador y Socio."""
from datetime import date
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy import Date, func, or_, select

from app.auth.routes import authenticated_user
from app.models import EventoAuditoria, Sucursal

router = APIRouter(prefix="/api/audit", tags=["Auditoría"])

# No se expone el JSON arbitrario de eventos históricos.
SAFE_KEYS = {
    "usuario_nombre", "user_name", "entidad_id", "sucursal_id", "sucursal_nombre",
    "destino_id", "destino_nombre", "cambios", "anterior", "nuevo", "motivo", "pedido_id",
    "estado_anterior", "estado_nuevo", "estado", "producto_id", "lote_id",
    "precio_anterior", "precio_nuevo", "old_price", "new_price", "transferencias",
    "previous_price", "product_sku", "product_name", "resultado", "simulado",
    "cantidad_sin_cambios", "vencimiento_sin_cambios", "transferencia_id",
}
SECRET_PARTS = ("password", "contraseña", "token", "secret", "hash", "qr")


def safe_value(value):
    if isinstance(value, dict):
        return {key: safe_value(item) for key, item in value.items()
                if not any(part in key.lower() for part in SECRET_PARTS)}
    if isinstance(value, list):
        return [safe_value(item) for item in value]
    return value


@router.get("")
def list_audit(
    request: Request,
    authenticated: Annotated[tuple, Depends(authenticated_user)],
    branch_id: UUID | None = None,
    date_from: date | None = None,
    date_to: date | None = None,
    page: Annotated[int, Query(ge=1, le=100000)] = 1,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
):
    actor, _ = authenticated
    if not {"ADMINISTRADOR", "SOCIO"}.intersection(actor.roles):
        raise HTTPException(403, "No tienes permiso para consultar la auditoría.")
    if date_from and date_to and date_from > date_to:
        raise HTTPException(422, "La fecha inicial no puede ser posterior a la fecha final.")
    event = EventoAuditoria
    conditions = []
    if branch_id:
        conditions.append(or_(event.sucursal_id == branch_id,
                              event.datos_cambio["sucursal_id"].astext == str(branch_id),
                              event.datos_cambio["destino_id"].astext == str(branch_id)))
    local_date = func.timezone("America/Santiago", event.ocurrido_en).cast(Date)
    if date_from:
        conditions.append(local_date >= date_from)
    if date_to:
        conditions.append(local_date <= date_to)
    with request.app.state.users.session_factory() as db:
        branches = {str(row.id): row.nombre for row in db.scalars(select(Sucursal))}
        for historical_id, name in db.execute(select(
            event.datos_cambio["sucursal_id"].astext,
            event.datos_cambio["sucursal_nombre"].astext,
        ).distinct()):
            if historical_id and name:
                branches.setdefault(historical_id, name + " (histórica)")
        total = db.scalar(select(func.count()).select_from(event).where(*conditions))
        rows = db.scalars(select(event).where(*conditions)
                          .order_by(event.ocurrido_en.desc(), event.secuencia.desc())
                          .offset((page - 1) * limit).limit(limit))
        events = []
        for row in rows:
            data = row.datos_cambio
            branch = str(row.sucursal_id) if row.sucursal_id else data.get("sucursal_id")
            events.append({
                "id": str(row.id), "at": row.ocurrido_en.isoformat(),
                "action": row.accion, "reference": row.referencia_historica,
                "actor": {"id": str(row.usuario_id) if row.usuario_id else None,
                          "name": data.get("usuario_nombre") or data.get("user_name")
                          or ("Nombre no disponible" if row.usuario_id else row.origen_actor)},
                "branch": {"id": branch, "name": data.get("sucursal_nombre")
                           or branches.get(branch, "Sucursal histórica")} if branch else None,
                "data": {key: safe_value(value) for key, value in data.items() if key in SAFE_KEYS},
            })
    return {"events": events, "total": total, "page": page, "limit": limit,
            "branches": [{"id": key, "name": name} for key, name in sorted(branches.items(), key=lambda pair: pair[1])]}
