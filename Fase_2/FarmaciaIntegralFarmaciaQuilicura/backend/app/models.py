from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import Boolean, CheckConstraint, Column, DateTime, ForeignKey, String, Table
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


usuario_rol = Table(
    "usuario_rol",
    Base.metadata,
    Column("usuario_id", ForeignKey("usuario_interno.id", ondelete="RESTRICT"), primary_key=True),
    Column("rol_id", ForeignKey("rol.id", ondelete="RESTRICT"), primary_key=True),
)
rol_permiso = Table(
    "rol_permiso",
    Base.metadata,
    Column("rol_id", ForeignKey("rol.id", ondelete="RESTRICT"), primary_key=True),
    Column("permiso_id", ForeignKey("permiso.id", ondelete="RESTRICT"), primary_key=True),
)


class Sucursal(Base):
    __tablename__ = "sucursal"
    __table_args__ = (
        CheckConstraint("btrim(codigo) <> ''", name="ck_sucursal_codigo"),
        CheckConstraint("btrim(nombre) <> ''", name="ck_sucursal_nombre"),
    )
    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    codigo: Mapped[str] = mapped_column(String(30), unique=True)
    nombre: Mapped[str] = mapped_column(String(150))
    direccion_local: Mapped[str] = mapped_column(String(250))
    activa: Mapped[bool] = mapped_column(Boolean, default=True)


class UsuarioInterno(Base):
    __tablename__ = "usuario_interno"
    __table_args__ = (
        CheckConstraint("btrim(nombre) <> ''", name="ck_usuario_nombre"),
        CheckConstraint("correo = lower(btrim(correo))", name="ck_usuario_correo_normalizado"),
    )
    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    nombre: Mapped[str] = mapped_column(String(150))
    correo: Mapped[str] = mapped_column(String(254), unique=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    activo: Mapped[bool] = mapped_column(Boolean, default=True)
    sucursal_id: Mapped[UUID] = mapped_column(
        ForeignKey("sucursal.id", ondelete="RESTRICT"), index=True
    )
    sucursal: Mapped[Sucursal] = relationship(lazy="joined")
    roles: Mapped[list["Rol"]] = relationship(secondary=usuario_rol, lazy="selectin")

    def permisos_efectivos(self) -> set[str]:
        return {permiso.codigo for rol in self.roles for permiso in rol.permisos}


class Rol(Base):
    __tablename__ = "rol"
    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    codigo: Mapped[str] = mapped_column(String(60), unique=True)
    nombre: Mapped[str] = mapped_column(String(100))
    permisos: Mapped[list["Permiso"]] = relationship(secondary=rol_permiso, lazy="selectin")


class Permiso(Base):
    __tablename__ = "permiso"
    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    codigo: Mapped[str] = mapped_column(String(100), unique=True)
    descripcion: Mapped[str] = mapped_column(String(250))


class SesionInterna(Base):
    __tablename__ = "sesion_interna"
    __table_args__ = (
        CheckConstraint("expira_en > creada_en", name="ck_sesion_expiracion"),
        CheckConstraint(
            "revocada_en IS NULL OR revocada_en >= creada_en", name="ck_sesion_revocacion"
        ),
    )
    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    usuario_id: Mapped[UUID] = mapped_column(
        ForeignKey("usuario_interno.id", ondelete="RESTRICT"), index=True
    )
    token_hash: Mapped[str] = mapped_column(String(64), unique=True)
    creada_en: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    expira_en: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    revocada_en: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
