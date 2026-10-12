from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    String,
    Text,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.models import Base


class Cliente(Base):
    __tablename__ = "cliente"
    __table_args__ = (
        CheckConstraint("btrim(nombre) <> ''", name="ck_cliente_nombre"),
        CheckConstraint("correo = lower(btrim(correo)) AND correo <> ''", name="ck_cliente_correo_normalizado"),
        CheckConstraint("password_hash LIKE '$argon2id$%'", name="ck_cliente_hash_argon2"),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    nombre: Mapped[str] = mapped_column(String(150))
    correo: Mapped[str] = mapped_column(String(254), unique=True)
    password_hash: Mapped[str] = mapped_column(Text)
    activo: Mapped[bool] = mapped_column(Boolean, default=True, server_default="true")
    creado_en: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class SesionCliente(Base):
    __tablename__ = "sesion_cliente"
    __table_args__ = (
        CheckConstraint("expira_en > creada_en", name="ck_sesion_cliente_expiracion"),
        CheckConstraint("revocada_en IS NULL OR revocada_en >= creada_en", name="ck_sesion_cliente_revocacion"),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    cliente_id: Mapped[UUID] = mapped_column(ForeignKey("cliente.id", ondelete="RESTRICT"), index=True)
    token_hash: Mapped[str] = mapped_column(String(64), unique=True)
    creada_en: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    expira_en: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    revocada_en: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
