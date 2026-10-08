from sqlalchemy import select, text

from app.models import SesionCaja, Venta, VentaDetalle


class PosRepository:
    def __init__(self, factory):
        self.factory = factory

    @staticmethod
    def lock(db, key):
        db.execute(
            text("SELECT pg_advisory_xact_lock(hashtextextended(:key, 0))"),
            {"key": f"pos:{key}"},
        )

    @staticmethod
    def current_cash(db, actor):
        return db.scalar(
            select(SesionCaja)
            .where(
                SesionCaja.usuario_id == actor.id,
                SesionCaja.sucursal_id == actor.branch_id,
                SesionCaja.cierre_en.is_(None),
            )
            .with_for_update()
        )

    @staticmethod
    def sales(db, cash_id):
        return list(
            db.scalars(
                select(Venta).where(Venta.sesion_caja_id == cash_id).order_by(Venta.id)
            )
        )

    @staticmethod
    def details(db, sale_id):
        return list(
            db.scalars(
                select(VentaDetalle)
                .where(VentaDetalle.venta_id == sale_id)
                .order_by(VentaDetalle.id)
            )
        )
