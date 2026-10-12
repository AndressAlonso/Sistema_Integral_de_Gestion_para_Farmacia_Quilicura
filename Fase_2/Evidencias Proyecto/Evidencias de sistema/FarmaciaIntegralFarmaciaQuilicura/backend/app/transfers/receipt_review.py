"""Revisión y reactivación explícita de lotes destino; no incorpora mercadería."""
from datetime import datetime, timezone

from sqlalchemy import select

from app.inventory.lot_status import LotStatusService
from app.models import InventarioSucursal, LoteInventario
from app.transfers.service import TransferError, TransferService


class ReceiptReviewService:
    def __init__(self, repository):
        self.repo = repository

    def context(self, db, actor, transfer_id, lock=False):
        TransferService.authorize(actor, "recibir")
        row = self.repo.get(db, transfer_id)
        if row is None:
            raise TransferError(404, "La transferencia no existe.")
        TransferService.check_scope(actor, row)
        if "ADMINISTRADOR" not in actor.roles and actor.branch_id != row.destino_id:
            raise TransferError(403, "La revisión debe realizarse desde la sucursal destino.")
        if lock:
            self.repo.branches(db, [row.origen_id, row.destino_id])
            row = self.repo.get(db, transfer_id, lock=True)
        if row.estado != "EN_TRANSITO":
            raise TransferError(409, "La transferencia ya no está en tránsito. Actualiza el detalle.")
        if not row.destino.activa or not row.origen.activa:
            raise TransferError(409, "Las sucursales deben estar activas para continuar.")
        return row

    def review(self, actor, transfer_id):
        with self.repo.factory() as db:
            row = self.context(db, actor, transfer_id)
            today = datetime.now(timezone.utc).date()
            items = []
            for detail in row.detalles:
                inventory = db.scalar(select(InventarioSucursal).where(
                    InventarioSucursal.producto_id == detail.producto_id,
                    InventarioSucursal.sucursal_id == row.destino_id))
                for allocation in detail.lotes:
                    source = allocation.lote_origen
                    lot = self.repo.destination_lot(db, inventory.id, source) if inventory else None
                    conflicts = []
                    if lot is not None and not lot.activo:
                        conflicts.append("INACTIVE")
                    if lot is not None and lot.fecha_vencimiento != source.fecha_vencimiento:
                        conflicts.append("EXPIRATION_MISMATCH")
                    items.append({"product_name": detail.producto.nombre, "number": source.numero_lote,
                        "incoming_quantity": allocation.cantidad, "source_expiration": source.fecha_vencimiento,
                        "destination_lot_id": lot.id if lot else None,
                        "destination_expiration": lot.fecha_vencimiento if lot else None,
                        "destination_active": lot.activo if lot else None,
                        "destination_quantity": lot.cantidad if lot else None, "conflicts": conflicts,
                        "can_reactivate": bool(lot and not lot.activo
                            and lot.fecha_vencimiento == source.fecha_vencimiento
                            and lot.fecha_vencimiento > today
                            and "inventario.gestionar_lotes" in actor.permissions)})
            return {"destination_name": row.destino.nombre, "items": items}

    def reactivate(self, actor, transfer_id, lot_id, data):
        with self.repo.factory.begin() as db:
            row = self.context(db, actor, transfer_id, lock=True)
            if "inventario.gestionar_lotes" not in actor.permissions:
                raise TransferError(403, "Necesitas permiso para gestionar lotes y registrar el motivo.")
            lot = db.scalar(select(LoteInventario).join(InventarioSucursal)
                .where(LoteInventario.id == lot_id, InventarioSucursal.sucursal_id == row.destino_id)
                .with_for_update(of=LoteInventario).execution_options(populate_existing=True))
            if lot is None:
                raise TransferError(404, "El lote no pertenece a la sucursal destino.")
            inventory = db.get(InventarioSucursal, lot.inventario_sucursal_id)
            source = next((allocation.lote_origen for detail in row.detalles
                if detail.producto_id == inventory.producto_id for allocation in detail.lotes
                if allocation.lote_origen.numero_lote == lot.numero_lote), None)
            if source is None:
                raise TransferError(409, "El lote no corresponde a los productos de esta transferencia.")
            if (lot.fecha_vencimiento != source.fecha_vencimiento
                    or lot.fecha_vencimiento <= datetime.now(timezone.utc).date()):
                raise TransferError(409, "El vencimiento no permite reactivar el lote para esta recepción. Revisa los datos.")
            return LotStatusService.reactivate_in_session(db, actor, lot.id, data, transfer_id=row.id)
