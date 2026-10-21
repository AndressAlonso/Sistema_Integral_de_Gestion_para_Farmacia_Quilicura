from datetime import datetime
from decimal import Decimal
from uuid import UUID, uuid4

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Integer,
    Numeric,
    String,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models import Base


class PedidoOnline(Base):
    __tablename__ = "pedido_online"
    __table_args__ = (
        CheckConstraint(
            "estado IN ('PENDIENTE_PAGO','CANCELADO','PAGADO','EN_PREPARACION','LISTO_PARA_RETIRO')", name="ck_pedido_estado"
        ),
        CheckConstraint("total >= 0", name="ck_pedido_total"),
        CheckConstraint(
            "btrim(nombre) <> '' AND btrim(correo) <> ''", name="ck_pedido_contacto"
        ),
    )
    id: Mapped[UUID] = mapped_column(primary_key=True)
    solicitud_hash: Mapped[str] = mapped_column(String(64))
    clave_hash: Mapped[str] = mapped_column(String(64))
    cliente_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("cliente.id", ondelete="RESTRICT"), index=True
    )
    sucursal_id: Mapped[UUID] = mapped_column(
        ForeignKey("sucursal.id", ondelete="RESTRICT"), index=True
    )
    nombre: Mapped[str] = mapped_column(String(150))
    correo: Mapped[str] = mapped_column(String(254))
    estado: Mapped[str] = mapped_column(
        String(30), default="PENDIENTE_PAGO", index=True
    )
    total: Mapped[Decimal] = mapped_column(Numeric(18, 2))
    creado_en: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    sucursal = relationship("Sucursal")
    detalles: Mapped[list["PedidoDetalle"]] = relationship(
        order_by="PedidoDetalle.producto_id"
    )


class PedidoDetalle(Base):
    __tablename__ = "pedido_detalle"
    __table_args__ = (
        UniqueConstraint("pedido_id", "producto_id", name="uq_pedido_producto"),
        CheckConstraint(
            "cantidad > 0 AND precio_unitario >= 0 AND subtotal >= 0",
            name="ck_pedido_detalle_valores",
        ),
    )
    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    pedido_id: Mapped[UUID] = mapped_column(
        ForeignKey("pedido_online.id", ondelete="RESTRICT"), index=True
    )
    producto_id: Mapped[UUID] = mapped_column(
        ForeignKey("producto.id", ondelete="RESTRICT")
    )
    nombre: Mapped[str] = mapped_column(String(200))
    cantidad: Mapped[int] = mapped_column(Integer)
    precio_unitario: Mapped[Decimal] = mapped_column(Numeric(14, 2))
    precio_base: Mapped[Decimal] = mapped_column(Numeric(14, 2))
    subtotal: Mapped[Decimal] = mapped_column(Numeric(18, 2))
    promocion: Mapped[str | None] = mapped_column(String(150))


class ReservaPedido(Base):
    __tablename__ = "reserva_pedido"
    __table_args__ = (
        UniqueConstraint("detalle_id", "lote_id", name="uq_reserva_pedido_lote"),
        CheckConstraint("cantidad > 0", name="ck_reserva_pedido_cantidad"),
    )
    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    pedido_id: Mapped[UUID] = mapped_column(
        ForeignKey("pedido_online.id", ondelete="RESTRICT"), index=True
    )
    detalle_id: Mapped[UUID] = mapped_column(
        ForeignKey("pedido_detalle.id", ondelete="RESTRICT")
    )
    lote_id: Mapped[UUID] = mapped_column(
        ForeignKey("lote_inventario.id", ondelete="RESTRICT"), index=True
    )
    cantidad: Mapped[int] = mapped_column(Integer)
    activa: Mapped[bool] = mapped_column(Boolean, default=True, index=True)
