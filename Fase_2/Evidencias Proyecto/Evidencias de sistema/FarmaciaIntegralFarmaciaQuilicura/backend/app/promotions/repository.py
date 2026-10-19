from uuid import UUID

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from app.models import Categoria, EventoAuditoria, Producto, Promocion
from app.pos.pricing import Promotion
from app.promotions.schemas import PromotionInput, PromotionResponse


class PromotionRepository:
    def __init__(self, factory):
        self.factory = factory

    @staticmethod
    def response(row):
        return PromotionResponse(id=row.id, name=row.nombre, kind=row.tipo,
            value=row.valor, starts_at=row.inicia_en, ends_at=row.termina_en,
            product_id=row.producto_id, category_id=row.categoria_id,
            is_active=row.activo, created_at=row.creado_en)

    def list(self):
        with self.factory() as db:
            return [self.response(row) for row in db.scalars(
                select(Promocion).order_by(Promocion.creado_en.desc(), Promocion.id))]

    @staticmethod
    def pricing(db):
        # El motor compartido evalúa vigencia y elige el menor precio.
        return tuple(Promotion(str(row.id), row.nombre, row.tipo, row.valor,
            row.inicia_en, row.termina_en, row.producto_id, row.categoria_id)
            for row in db.scalars(select(Promocion).where(Promocion.activo.is_(True))))

    def save(self, data: PromotionInput, actor, promotion_id: UUID | None = None):
        try:
            with self.factory.begin() as db:
                if data.product_id is not None:
                    product = db.get(Producto, data.product_id)
                    if product is None or not product.activo:
                        raise HTTPException(422, "Selecciona un producto activo existente.")
                elif db.get(Categoria, data.category_id) is None:
                    raise HTTPException(422, "Selecciona una categoría existente.")
                if promotion_id is None:
                    row = Promocion()
                    db.add(row)
                    before = None
                else:
                    row = db.scalar(select(Promocion).where(Promocion.id == promotion_id).with_for_update())
                    if row is None:
                        raise HTTPException(404, "La promoción no existe.")
                    before = self.response(row).model_dump(mode="json")
                row.nombre, row.tipo, row.valor = data.name, data.kind, data.value
                row.inicia_en, row.termina_en = data.starts_at, data.ends_at
                row.producto_id, row.categoria_id = data.product_id, data.category_id
                row.activo = data.is_active
                db.flush()
                response = self.response(row)
                db.add(EventoAuditoria(usuario_id=actor.id, origen_actor="USUARIO_INTERNO",
                    accion="CREAR_PROMOCION" if before is None else "ACTUALIZAR_PROMOCION",
                    referencia_historica=str(row.id), producto_id=row.producto_id,
                    datos_cambio={"anterior": before, "nuevo": response.model_dump(mode="json")}))
            return response
        except IntegrityError:
            raise HTTPException(409, "Los datos cambiaron. Actualiza el listado y revisa la promoción.") from None
