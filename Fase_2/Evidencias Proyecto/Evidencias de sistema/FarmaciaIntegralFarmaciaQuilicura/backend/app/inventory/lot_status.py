"""Estado de lotes en Inventario: permisos, motivo y auditoría, sin movimientos."""
from datetime import date, datetime, timezone
from typing import Literal
from uuid import UUID

from fastapi import HTTPException
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import select

from app.models import EventoAuditoria, InventarioSucursal, LoteInventario, Sucursal


class ReactivateLot(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    reason: str = Field(min_length=3, max_length=250)
    confirmed: Literal[True]
    expected_expiration_date: date
    expected_quantity: int = Field(strict=True, ge=0)


class DisableLot(ReactivateLot):
    """Mismo respaldo y comprobación de datos para bloquear un lote."""


class LotStatusResponse(BaseModel):
    lot_id: UUID
    number: str
    product_name: str
    branch_name: str
    expiration_date: date
    quantity: int
    is_active: bool
    can_reactivate: bool
    can_disable: bool


class LotReactivationResult(BaseModel):
    lot_id: UUID
    changed: bool


class LotStatusService:
    def __init__(self, factory):
        self.factory = factory

    @staticmethod
    def context(db, actor, lot_id, lock=False):
        lot = db.get(LoteInventario, lot_id)
        if lot is None:
            raise HTTPException(404, "El lote no existe.")
        inventory = db.get(InventarioSucursal, lot.inventario_sucursal_id)
        if "ADMINISTRADOR" not in actor.roles and actor.branch_id != inventory.sucursal_id:
            raise HTTPException(403, "El lote no corresponde a tu sucursal.")
        if lock:
            db.scalar(select(Sucursal).where(Sucursal.id == inventory.sucursal_id).with_for_update(read=True))
            inventory = db.scalar(select(InventarioSucursal).where(InventarioSucursal.id == inventory.id)
                .with_for_update(of=InventarioSucursal).execution_options(populate_existing=True))
            lot = db.scalar(select(LoteInventario).where(LoteInventario.id == lot_id)
                .with_for_update().execution_options(populate_existing=True))
        return lot, inventory

    def get(self, actor, lot_id):
        with self.factory() as db:
            lot, inventory = self.context(db, actor, lot_id)
            return {"lot_id": lot.id, "number": lot.numero_lote, "product_name": inventory.producto.nombre,
                "branch_name": inventory.sucursal.nombre, "expiration_date": lot.fecha_vencimiento,
                "quantity": lot.cantidad, "is_active": lot.activo,
                "can_disable": bool(actor.is_active and "inventario.gestionar_lotes" in actor.permissions
                    and inventory.sucursal.activa and lot.activo),
                "can_reactivate": bool(actor.is_active and "inventario.gestionar_lotes" in actor.permissions
                    and inventory.sucursal.activa and not lot.activo
                    and lot.fecha_vencimiento > datetime.now(timezone.utc).date())}

    @staticmethod
    def reactivate_in_session(db, actor, lot_id, data, transfer_id=None):
        if not actor.is_active or "inventario.gestionar_lotes" not in actor.permissions:
            raise HTTPException(403, "Necesitas permiso para gestionar lotes.")
        lot, inventory = LotStatusService.context(db, actor, lot_id, lock=True)
        if not inventory.sucursal.activa:
            raise HTTPException(409, "La sucursal está inactiva. No se puede reactivar el lote.")
        if lot.fecha_vencimiento <= datetime.now(timezone.utc).date():
            raise HTTPException(409, "El lote está vencido o vence hoy. No se puede reactivar para su uso.")
        if lot.fecha_vencimiento != data.expected_expiration_date or lot.cantidad != data.expected_quantity:
            raise HTTPException(409, "El lote cambió. Actualiza la revisión antes de reactivar.")
        if lot.activo:
            return {"lot_id": lot.id, "changed": False}
        lot.activo = True
        changes = {"motivo": data.reason, "anterior": {"activo": False}, "nuevo": {"activo": True},
            "cantidad_sin_cambios": lot.cantidad, "vencimiento_sin_cambios": lot.fecha_vencimiento.isoformat()}
        if transfer_id is not None:
            changes["transferencia_id"] = str(transfer_id)
        db.add(EventoAuditoria(usuario_id=actor.id, sucursal_id=inventory.sucursal_id,
            producto_id=inventory.producto_id, origen_actor="USUARIO_INTERNO",
            accion="LOTE_REACTIVADO", referencia_historica=str(lot.id), datos_cambio=changes))
        db.flush()
        return {"lot_id": lot.id, "changed": True}

    def reactivate(self, actor, lot_id, data):
        with self.factory.begin() as db:
            return self.reactivate_in_session(db, actor, lot_id, data)


    def disable(self, actor, lot_id, data):
        if not actor.is_active or "inventario.gestionar_lotes" not in actor.permissions:
            raise HTTPException(403, "Necesitas permiso para gestionar lotes.")
        with self.factory.begin() as db:
            lot, inventory = self.context(db, actor, lot_id, lock=True)
            if not inventory.sucursal.activa:
                raise HTTPException(409, "La sucursal está inactiva. No se puede deshabilitar el lote.")
            if lot.fecha_vencimiento != data.expected_expiration_date or lot.cantidad != data.expected_quantity:
                raise HTTPException(409, "El lote cambió. Actualiza la revisión antes de deshabilitar.")
            if not lot.activo:
                return {"lot_id": lot.id, "changed": False}
            lot.activo = False
            db.add(EventoAuditoria(
                usuario_id=actor.id, sucursal_id=inventory.sucursal_id,
                producto_id=inventory.producto_id, origen_actor="USUARIO_INTERNO",
                accion="LOTE_DESHABILITADO", referencia_historica=str(lot.id),
                datos_cambio={"motivo": data.reason, "anterior": {"activo": True},
                    "nuevo": {"activo": False}, "cantidad_sin_cambios": lot.cantidad,
                    "vencimiento_sin_cambios": lot.fecha_vencimiento.isoformat()},
            ))
            db.flush()
            return {"lot_id": lot.id, "changed": True}
