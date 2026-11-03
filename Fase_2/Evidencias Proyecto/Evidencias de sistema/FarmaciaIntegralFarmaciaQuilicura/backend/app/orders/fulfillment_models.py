"""E7-H5/H6: credencial privada sin caducidad y bandeja de salida durable."""
import secrets
from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    Integer,
    String,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.models import Base


def new_manual_code():
    return f"{secrets.randbelow(10**16):016d}"


class RetiroPedido(Base):
    __tablename__ = "retiro_pedido"
    __table_args__ = (
        UniqueConstraint("codigo_manual", name="uq_retiro_codigo_manual"),
        CheckConstraint("codigo_manual ~ '^[0-9]{16}$'", name="ck_retiro_codigo_manual"),
    )
    pedido_id: Mapped[UUID] = mapped_column(ForeignKey("pedido_online.id", ondelete="RESTRICT"), primary_key=True)
    codigo: Mapped[str] = mapped_column(String(64))
    codigo_hash: Mapped[str] = mapped_column(String(64), unique=True)
    codigo_manual: Mapped[str] = mapped_column(String(16), default=new_manual_code)
    listo_en: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    retirado_en: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    usuario_id: Mapped[UUID | None] = mapped_column()
    usuario_nombre: Mapped[str | None] = mapped_column(String(150))


class CorreoPedido(Base):
    __tablename__ = "correo_pedido"
    __table_args__ = (UniqueConstraint("pedido_id", "tipo", name="uq_correo_pedido_tipo"),)
    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    pedido_id: Mapped[UUID] = mapped_column(ForeignKey("pedido_online.id", ondelete="RESTRICT"), index=True)
    tipo: Mapped[str] = mapped_column(String(20))
    estado: Mapped[str] = mapped_column(String(20), default="PENDIENTE")
    intentos: Mapped[int] = mapped_column(Integer, default=0)
    proximo_intento: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    enviado_en: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
