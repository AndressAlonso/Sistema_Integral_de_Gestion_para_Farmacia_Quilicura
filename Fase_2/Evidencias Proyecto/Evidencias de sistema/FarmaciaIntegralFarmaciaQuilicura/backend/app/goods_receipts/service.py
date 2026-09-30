"""E4-H4: entrada atómica e idempotente, sin modificar las reservas existentes."""

from datetime import datetime, timezone
from hashlib import sha256

from app.models import (
    LoteInventario,
    MovimientoInventario,
    RecepcionMercaderia,
    RecepcionMercaderiaDetalle,
)

PERMISSION = "inventario.registrar_entrada"


class ReceiptError(Exception):
    def __init__(self, status, message):
        self.status = status
        self.message = message
        super().__init__(message)


class ReceiptService:
    def __init__(self, repository):
        self.repository = repository

    @staticmethod
    def authorize(actor, branch_id=None):
        if not actor.is_active or PERMISSION not in actor.permissions:
            raise ReceiptError(403, "No tienes permiso para registrar entradas de mercadería.")
        if branch_id is not None and branch_id != actor.branch_id and "ADMINISTRADOR" not in actor.roles:
            raise ReceiptError(403, "Solo puedes registrar entradas en tu sucursal asignada.")

    def options(self, actor):
        self.authorize(actor)
        with self.repository.factory() as db:
            return self.repository.options(db, None if "ADMINISTRADOR" in actor.roles else actor.branch_id)

    def get(self, actor, receipt_id):
        self.authorize(actor)
        with self.repository.factory() as db:
            row = self.repository.receipt(db, receipt_id)
            if row is None:
                raise ReceiptError(404, "La recepción no existe.")
            self.authorize(actor, row.sucursal_id)
            return self.repository.response(row)

    def create(self, actor, data):
        self.authorize(actor, data.branch_id)
        fingerprint = sha256(data.model_dump_json().encode()).hexdigest()
        with self.repository.factory.begin() as db:
            self.repository.lock_request(db, data.request_id)
            existing = self.repository.receipt(db, data.request_id)
            if existing is not None:
                if existing.usuario_id != actor.id or existing.solicitud_hash != fingerprint:
                    raise ReceiptError(409, "La solicitud ya fue utilizada con otros datos.")
                return self.repository.response(existing), False

            today = datetime.now(timezone.utc).date()
            if data.document_date > today:
                raise ReceiptError(422, "La fecha del documento no puede ser futura.")
            branch = self.repository.branch(db, data.branch_id)
            if branch is None or not branch.activa:
                raise ReceiptError(409, "La sucursal no existe o está inactiva.")
            receipt = RecepcionMercaderia(
                id=data.request_id, solicitud_hash=fingerprint, sucursal_id=data.branch_id,
                usuario_id=actor.id, proveedor=data.supplier, tipo_documento=data.document_type,
                numero_documento=data.document_number, fecha_documento=data.document_date,
            )
            db.add(receipt)
            # Orden estable de bloqueos para recepciones simultáneas de varios productos.
            for item in sorted(data.items, key=lambda i: (str(i.product_id), i.lot_number)):
                if item.expiration_date <= today:
                    raise ReceiptError(422, "El vencimiento de cada lote debe ser futuro.")
                product = self.repository.product(db, item.product_id)
                if product is None or not product.activo:
                    raise ReceiptError(409, "Un producto no existe o está inactivo.")
                inventory = self.repository.inventory(db, item.product_id, data.branch_id)
                lot = self.repository.lot(db, inventory.id, item.lot_number)
                if lot is not None and (not lot.activo or lot.fecha_vencimiento != item.expiration_date):
                    raise ReceiptError(409, "El lote ya existe con otro vencimiento o está inactivo.")
                if inventory.stock_fisico + item.quantity > 2_147_483_647:
                    raise ReceiptError(409, "La cantidad supera el límite admitido de existencias.")
                if lot is None:
                    lot = LoteInventario(
                        inventario_sucursal_id=inventory.id, numero_lote=item.lot_number,
                        fecha_vencimiento=item.expiration_date, cantidad=0, activo=True,
                    )
                    db.add(lot)
                if lot.cantidad + item.quantity > 2_147_483_647:
                    raise ReceiptError(409, "La cantidad supera el límite admitido del lote.")
                before = inventory.stock_fisico
                inventory.stock_fisico += item.quantity
                lot.cantidad += item.quantity
                db.flush()
                db.add(RecepcionMercaderiaDetalle(
                    recepcion_id=receipt.id, lote_id=lot.id, cantidad=item.quantity,
                ))
                db.add(MovimientoInventario(
                    inventario_sucursal_id=inventory.id, usuario_id=actor.id, tipo="RECEPCION",
                    cantidad_fisica=item.quantity, cantidad_reservada=0,
                    stock_fisico_anterior=before, stock_fisico_resultante=inventory.stock_fisico,
                    stock_reservado_anterior=inventory.stock_reservado,
                    stock_reservado_resultante=inventory.stock_reservado,
                    motivo=f"Entrada por {data.document_type.lower()} {data.document_number}",
                    referencia_tipo="RECEPCION_MERCADERIA", referencia_id=receipt.id,
                ))
            db.flush()
            return self.repository.response(receipt), True
