"""E7-H2: una preferencia de checkout persistida por pedido online."""

from datetime import datetime
from decimal import Decimal
from uuid import UUID

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    Numeric,
    String,
    Text,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.models import Base


class CheckoutMercadoPago(Base):
    __tablename__ = "checkout_mercadopago"
    __table_args__ = (
        CheckConstraint(
            "estado IN ('CREANDO','LISTO','INCIERTO')", name="ck_checkout_mp_estado"
        ),
        CheckConstraint("total > 0 AND moneda = 'CLP'", name="ck_checkout_mp_importe"),
        CheckConstraint("vence_en > creado_en", name="ck_checkout_mp_plazo"),
        CheckConstraint(
            "(estado = 'LISTO' AND preferencia_id IS NOT NULL "
            "AND btrim(preferencia_id) <> '' AND checkout_url IS NOT NULL "
            "AND btrim(checkout_url) <> '') OR "
            "(estado IN ('CREANDO','INCIERTO') AND preferencia_id IS NULL "
            "AND checkout_url IS NULL)",
            name="ck_checkout_mp_enlace",
        ),
    )

    pedido_id: Mapped[UUID] = mapped_column(
        ForeignKey("pedido_online.id", ondelete="RESTRICT"), primary_key=True
    )
    estado: Mapped[str] = mapped_column(String(20), default="CREANDO")
    preferencia_id: Mapped[str | None] = mapped_column(String(200), unique=True)
    checkout_url: Mapped[str | None] = mapped_column(Text)
    total: Mapped[Decimal] = mapped_column(Numeric(18, 2))
    moneda: Mapped[str] = mapped_column(String(3), default="CLP")
    creado_en: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    actualizado_en: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    vence_en: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class PagoMercadoPago(Base):
    """Último estado consultado al proveedor, sin almacenar datos del comprador."""

    __tablename__ = "pago_mercadopago"
    __table_args__ = (
        CheckConstraint("total > 0 AND moneda = 'CLP'", name="ck_pago_mp_importe"),
    )
    id: Mapped[str] = mapped_column(String(30), primary_key=True)
    pedido_id: Mapped[UUID] = mapped_column(
        ForeignKey("pedido_online.id", ondelete="RESTRICT"), index=True
    )
    estado: Mapped[str] = mapped_column(String(30))
    total: Mapped[Decimal] = mapped_column(Numeric(18, 2))
    moneda: Mapped[str] = mapped_column(String(3))
    proveedor_actualizado_en: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    aprobado_en: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    procesado_en: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    revision_motivo: Mapped[str | None] = mapped_column(String(100))
