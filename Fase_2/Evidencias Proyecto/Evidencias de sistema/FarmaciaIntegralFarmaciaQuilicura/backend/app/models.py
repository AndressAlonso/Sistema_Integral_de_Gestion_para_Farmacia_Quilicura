from datetime import date, datetime
from decimal import Decimal
from uuid import UUID, uuid4

from sqlalchemy import (
    BigInteger,
    Boolean,
    CheckConstraint,
    Column,
    Date,
    DateTime,
    ForeignKey,
    Identity,
    Index,
    Integer,
    Numeric,
    String,
    Table,
    Text,
    UniqueConstraint,
    false,
    func,
    true,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import (
    DeclarativeBase,
    Mapped,
    mapped_column,
    relationship,
)


class Base(DeclarativeBase):
    pass


class ReversaVenta(Base):
    __tablename__ = "reversa_venta"
    __table_args__ = (
        CheckConstraint("tipo IN ('ANULACION','DEVOLUCION')", name="ck_reversa_tipo"),
        CheckConstraint("btrim(motivo) <> '' AND importe >= 0", name="ck_reversa_datos"),
    )
    id: Mapped[UUID] = mapped_column(primary_key=True)
    solicitud_hash: Mapped[str] = mapped_column(String(64))
    venta_id: Mapped[UUID] = mapped_column(ForeignKey("venta.id", ondelete="RESTRICT"), index=True)
    usuario_id: Mapped[UUID] = mapped_column(ForeignKey("usuario_interno.id", ondelete="RESTRICT"))
    sesion_caja_id: Mapped[UUID] = mapped_column(ForeignKey("sesion_caja.id", ondelete="RESTRICT"), index=True)
    fecha: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    tipo: Mapped[str] = mapped_column(String(20))
    motivo: Mapped[str] = mapped_column(String(250))
    importe: Mapped[Decimal] = mapped_column(Numeric(14, 2))


class ReversaVentaDetalle(Base):
    __tablename__ = "reversa_venta_detalle"
    __table_args__ = (
        UniqueConstraint("reversa_id", "venta_lote_id", name="uq_reversa_lote"),
        CheckConstraint("cantidad > 0 AND btrim(motivo_condicion) <> ''", name="ck_reversa_detalle"),
    )
    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    reversa_id: Mapped[UUID] = mapped_column(ForeignKey("reversa_venta.id", ondelete="RESTRICT"))
    venta_lote_id: Mapped[UUID] = mapped_column(ForeignKey("venta_lote.id", ondelete="RESTRICT"))
    cantidad: Mapped[int] = mapped_column(Integer)
    reintegrar_stock: Mapped[bool] = mapped_column(Boolean)
    motivo_condicion: Mapped[str] = mapped_column(String(250))


class SesionCaja(Base):
    __tablename__ = "sesion_caja"
    __table_args__ = (
        Index("uq_caja_abierta_usuario_sucursal", "usuario_id", "sucursal_id", unique=True,
              postgresql_where=Column("cierre_en").is_(None)),
        CheckConstraint("monto_inicial >= 0", name="ck_caja_monto"),
        CheckConstraint("(cierre_en IS NULL AND efectivo_contado IS NULL AND resumen_cierre IS NULL) OR "
                        "(cierre_en >= apertura_en AND efectivo_contado >= 0 AND resumen_cierre IS NOT NULL)",
                        name="ck_caja_cierre"),
    )
    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    usuario_id: Mapped[UUID] = mapped_column(ForeignKey("usuario_interno.id", ondelete="RESTRICT"))
    sucursal_id: Mapped[UUID] = mapped_column(ForeignKey("sucursal.id", ondelete="RESTRICT"))
    apertura_en: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    monto_inicial: Mapped[Decimal] = mapped_column(Numeric(14, 2))
    cierre_en: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    efectivo_contado: Mapped[Decimal | None] = mapped_column(Numeric(14, 2))
    resumen_cierre: Mapped[dict | None] = mapped_column(JSONB)


class Venta(Base):
    __tablename__ = "venta"
    __table_args__ = (
        CheckConstraint("medio_pago IN ('EFECTIVO','DEBITO','CREDITO','TRANSFERENCIA')", name="ck_venta_pago"),
        CheckConstraint("subtotal >= 0 AND descuento >= 0 AND total >= 0 AND total = subtotal - descuento",
                        name="ck_venta_totales"),
    )
    id: Mapped[UUID] = mapped_column(primary_key=True)
    solicitud_hash: Mapped[str] = mapped_column(String(64))
    sesion_caja_id: Mapped[UUID] = mapped_column(ForeignKey("sesion_caja.id", ondelete="RESTRICT"), index=True)
    usuario_id: Mapped[UUID] = mapped_column(ForeignKey("usuario_interno.id", ondelete="RESTRICT"))
    sucursal_id: Mapped[UUID] = mapped_column(ForeignKey("sucursal.id", ondelete="RESTRICT"), index=True)
    fecha: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    medio_pago: Mapped[str] = mapped_column(String(20))
    subtotal: Mapped[Decimal] = mapped_column(Numeric(14, 2))
    descuento: Mapped[Decimal] = mapped_column(Numeric(14, 2))
    total: Mapped[Decimal] = mapped_column(Numeric(14, 2))


class VentaDetalle(Base):
    __tablename__ = "venta_detalle"
    __table_args__ = (
        UniqueConstraint("venta_id", "producto_id", name="uq_venta_producto"),
        CheckConstraint("cantidad > 0 AND precio_base >= 0 AND precio_final >= 0 AND "
                        "precio_final <= precio_base AND total = precio_final * cantidad", name="ck_venta_detalle"),
    )
    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    venta_id: Mapped[UUID] = mapped_column(ForeignKey("venta.id", ondelete="RESTRICT"))
    producto_id: Mapped[UUID] = mapped_column(ForeignKey("producto.id", ondelete="RESTRICT"))
    nombre: Mapped[str] = mapped_column(String(150))
    sku: Mapped[str] = mapped_column(String(64))
    cantidad: Mapped[int] = mapped_column(Integer)
    precio_base: Mapped[Decimal] = mapped_column(Numeric(14, 2))
    precio_final: Mapped[Decimal] = mapped_column(Numeric(14, 2))
    promocion: Mapped[dict | None] = mapped_column(JSONB)
    total: Mapped[Decimal] = mapped_column(Numeric(14, 2))


class VentaLote(Base):
    __tablename__ = "venta_lote"
    __table_args__ = (
        UniqueConstraint("venta_detalle_id", "lote_id", name="uq_venta_detalle_lote"),
        CheckConstraint("cantidad > 0", name="ck_venta_lote_cantidad"),
    )
    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    venta_detalle_id: Mapped[UUID] = mapped_column(ForeignKey("venta_detalle.id", ondelete="RESTRICT"))
    lote_id: Mapped[UUID] = mapped_column(ForeignKey("lote_inventario.id", ondelete="RESTRICT"))
    cantidad: Mapped[int] = mapped_column(Integer)


usuario_rol = Table(
    "usuario_rol",
    Base.metadata,
    Column(
        "usuario_id",
        ForeignKey(
            "usuario_interno.id",
            ondelete="RESTRICT",
        ),
        primary_key=True,
    ),
    Column(
        "rol_id",
        ForeignKey(
            "rol.id",
            ondelete="RESTRICT",
        ),
        primary_key=True,
    ),
)


rol_permiso = Table(
    "rol_permiso",
    Base.metadata,
    Column(
        "rol_id",
        ForeignKey(
            "rol.id",
            ondelete="RESTRICT",
        ),
        primary_key=True,
    ),
    Column(
        "permiso_id",
        ForeignKey(
            "permiso.id",
            ondelete="RESTRICT",
        ),
        primary_key=True,
    ),
)


class Sucursal(Base):
    __tablename__ = "sucursal"
    __table_args__ = (
        CheckConstraint(
            "btrim(codigo) <> ''",
            name="ck_sucursal_codigo",
        ),
        CheckConstraint(
            "btrim(nombre) <> ''",
            name="ck_sucursal_nombre",
        ),
    )

    id: Mapped[UUID] = mapped_column(
        primary_key=True,
        default=uuid4,
    )

    codigo: Mapped[str] = mapped_column(
        String(30),
        unique=True,
    )

    nombre: Mapped[str] = mapped_column(
        String(150),
    )

    direccion_local: Mapped[str] = mapped_column(
        String(250),
    )

    activa: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
    )


class UsuarioInterno(Base):
    __tablename__ = "usuario_interno"
    __table_args__ = (
        CheckConstraint(
            "btrim(nombre) <> ''",
            name="ck_usuario_nombre",
        ),
        CheckConstraint(
            "correo = lower(btrim(correo))",
            name="ck_usuario_correo_normalizado",
        ),
    )

    id: Mapped[UUID] = mapped_column(
        primary_key=True,
        default=uuid4,
    )

    nombre: Mapped[str] = mapped_column(
        String(150),
    )

    correo: Mapped[str] = mapped_column(
        String(254),
        unique=True,
    )

    password_hash: Mapped[str] = mapped_column(
        String(255),
    )

    activo: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
    )

    sucursal_id: Mapped[UUID] = mapped_column(
        ForeignKey(
            "sucursal.id",
            ondelete="RESTRICT",
        ),
        index=True,
    )

    sucursal: Mapped["Sucursal"] = relationship(
        lazy="joined",
    )

    roles: Mapped[list["Rol"]] = relationship(
        secondary=usuario_rol,
        lazy="selectin",
    )

    def permisos_efectivos(self) -> set[str]:
        permisos = {
            permiso.codigo
            for rol in self.roles
            for permiso in rol.permisos
        }

        return permisos


class Rol(Base):
    __tablename__ = "rol"

    id: Mapped[UUID] = mapped_column(
        primary_key=True,
        default=uuid4,
    )

    codigo: Mapped[str] = mapped_column(
        String(60),
        unique=True,
    )

    nombre: Mapped[str] = mapped_column(
        String(100),
    )

    permisos: Mapped[list["Permiso"]] = relationship(
        secondary=rol_permiso,
        lazy="selectin",
    )


class Permiso(Base):
    __tablename__ = "permiso"

    id: Mapped[UUID] = mapped_column(
        primary_key=True,
        default=uuid4,
    )

    codigo: Mapped[str] = mapped_column(
        String(100),
        unique=True,
    )

    descripcion: Mapped[str] = mapped_column(
        String(250),
    )


class SesionInterna(Base):
    __tablename__ = "sesion_interna"
    __table_args__ = (
        CheckConstraint(
            "expira_en > creada_en",
            name="ck_sesion_expiracion",
        ),
        CheckConstraint(
            "revocada_en IS NULL OR revocada_en >= creada_en",
            name="ck_sesion_revocacion",
        ),
    )

    id: Mapped[UUID] = mapped_column(
        primary_key=True,
        default=uuid4,
    )

    usuario_id: Mapped[UUID] = mapped_column(
        ForeignKey(
            "usuario_interno.id",
            ondelete="RESTRICT",
        ),
        index=True,
    )

    token_hash: Mapped[str] = mapped_column(
        String(64),
        unique=True,
    )

    creada_en: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
    )

    expira_en: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
    )

    revocada_en: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )


class Categoria(Base):
    __tablename__ = "categoria"
    __table_args__ = (
        CheckConstraint(
            "btrim(nombre) <> ''",
            name="ck_categoria_nombre",
        ),
    )

    id: Mapped[UUID] = mapped_column(
        primary_key=True,
        default=uuid4,
    )

    nombre: Mapped[str] = mapped_column(
        String(150),
    )

    productos: Mapped[list["Producto"]] = relationship(
        back_populates="categoria",
        passive_deletes="all",
    )


class Producto(Base):
    __tablename__ = "producto"
    __table_args__ = (
        UniqueConstraint(
            "sku",
            name="uq_producto_sku",
        ),
        CheckConstraint(
            "btrim(sku) <> '' AND sku = btrim(sku)",
            name="ck_producto_sku",
        ),
        CheckConstraint(
            "btrim(nombre) <> ''",
            name="ck_producto_nombre",
        ),
        CheckConstraint(
            "precio_actual >= 0 "
            "AND precio_actual < 1000000000000",
            name="ck_producto_precio_actual",
        ),
    )

    id: Mapped[UUID] = mapped_column(
        primary_key=True,
        default=uuid4,
    )

    sku: Mapped[str] = mapped_column(
        String(64),
    )

    nombre: Mapped[str] = mapped_column(
        String(150),
    )

    descripcion: Mapped[str] = mapped_column(
        Text,
    )

    activo: Mapped[bool] = mapped_column(
        Boolean,
        server_default=true(),
    )

    image_key: Mapped[str | None] = mapped_column(
        String(40),
        nullable=True,
    )

    publicado_online: Mapped[bool] = mapped_column(
        Boolean,
        server_default=false(),
    )

    requiere_receta: Mapped[bool] = mapped_column(
        Boolean,
    )

    precio_actual: Mapped[Decimal] = mapped_column(
        Numeric(14, 2),
    )

    categoria_id: Mapped[UUID] = mapped_column(
        ForeignKey(
            "categoria.id",
            ondelete="RESTRICT",
        ),
        index=True,
    )

    categoria: Mapped["Categoria"] = relationship(
        back_populates="productos",
    )

    codigos_barra: Mapped[list["CodigoBarra"]] = relationship(
        back_populates="producto",
        passive_deletes="all",
    )


class CodigoBarra(Base):
    __tablename__ = "codigo_barra"
    __table_args__ = (
        UniqueConstraint(
            "valor",
            name="uq_codigo_barra_valor",
        ),
        CheckConstraint(
            "btrim(valor) <> '' AND valor = btrim(valor)",
            name="ck_codigo_barra_valor",
        ),
    )

    id: Mapped[UUID] = mapped_column(
        primary_key=True,
        default=uuid4,
    )

    valor: Mapped[str] = mapped_column(
        String(128),
    )

    producto_id: Mapped[UUID] = mapped_column(
        ForeignKey(
            "producto.id",
            ondelete="RESTRICT",
        ),
        index=True,
    )

    producto: Mapped["Producto"] = relationship(
        back_populates="codigos_barra",
    )


class InventarioSucursal(Base):
    __tablename__ = "inventario_sucursal"
    __table_args__ = (
        UniqueConstraint(
            "producto_id",
            "sucursal_id",
            name="uq_inventario_producto_sucursal",
        ),
        CheckConstraint(
            "stock_fisico >= 0",
            name="ck_inventario_stock_fisico",
        ),
        CheckConstraint(
            "stock_reservado >= 0",
            name="ck_inventario_stock_reservado",
        ),
        CheckConstraint(
            "stock_reservado <= stock_fisico",
            name="ck_inventario_stock_reservado_fisico",
        ),
        CheckConstraint(
            "stock_minimo >= 0",
            name="ck_inventario_stock_minimo",
        ),
    )

    id: Mapped[UUID] = mapped_column(
        primary_key=True,
        default=uuid4,
    )

    producto_id: Mapped[UUID] = mapped_column(
        ForeignKey(
            "producto.id",
            ondelete="RESTRICT",
        ),
        index=True,
    )

    sucursal_id: Mapped[UUID] = mapped_column(
        ForeignKey(
            "sucursal.id",
            ondelete="RESTRICT",
        ),
        index=True,
    )

    stock_fisico: Mapped[int] = mapped_column(
        Integer,
        default=0,
        server_default="0",
    )

    stock_reservado: Mapped[int] = mapped_column(
        Integer,
        default=0,
        server_default="0",
    )

    stock_minimo: Mapped[int] = mapped_column(
        Integer,
        default=0,
        server_default="0",
    )

    producto: Mapped["Producto"] = relationship(
        lazy="joined",
    )

    sucursal: Mapped["Sucursal"] = relationship(
        lazy="joined",
    )

    lotes: Mapped[list["LoteInventario"]] = relationship(
        back_populates="inventario",
        passive_deletes="all",
        order_by="LoteInventario.fecha_vencimiento",
    )

    movimientos: Mapped[
        list["MovimientoInventario"]
    ] = relationship(
        back_populates="inventario",
        passive_deletes="all",
        order_by="MovimientoInventario.creado_en",
    )

    @property
    def stock_disponible(self) -> int:
        return self.stock_fisico - self.stock_reservado

    @property
    def bajo_stock_minimo(self) -> bool:
        return (
            self.stock_minimo > 0
            and self.stock_disponible <= self.stock_minimo
        )

    @property
    def estado_stock(self) -> str:
        if self.stock_disponible == 0:
            return "SIN_STOCK"

        if self.bajo_stock_minimo:
            return "BAJO"

        return "DISPONIBLE"


class LoteInventario(Base):
    __tablename__ = "lote_inventario"
    __table_args__ = (
        UniqueConstraint(
            "inventario_sucursal_id",
            "numero_lote",
            name="uq_lote_inventario_numero",
        ),
        CheckConstraint(
            "btrim(numero_lote) <> '' "
            "AND numero_lote = btrim(numero_lote)",
            name="ck_lote_inventario_numero",
        ),
        CheckConstraint(
            "cantidad >= 0",
            name="ck_lote_inventario_cantidad",
        ),
    )

    id: Mapped[UUID] = mapped_column(
        primary_key=True,
        default=uuid4,
    )

    inventario_sucursal_id: Mapped[UUID] = mapped_column(
        ForeignKey(
            "inventario_sucursal.id",
            ondelete="RESTRICT",
        ),
        index=True,
    )

    numero_lote: Mapped[str] = mapped_column(
        String(80),
    )

    fecha_vencimiento: Mapped[date] = mapped_column(
        Date,
        index=True,
    )

    cantidad: Mapped[int] = mapped_column(
        Integer,
        default=0,
        server_default="0",
    )

    activo: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        server_default=true(),
    )

    creado_en: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
    )

    inventario: Mapped["InventarioSucursal"] = relationship(
        back_populates="lotes",
    )


class MovimientoInventario(Base):
    __tablename__ = "movimiento_inventario"
    __table_args__ = (
        Index(
            "ix_movimiento_inventario_consulta",
            "inventario_sucursal_id",
            "creado_en",
        ),
        CheckConstraint(
            "btrim(tipo) <> '' "
            "AND tipo = btrim(tipo)",
            name="ck_movimiento_inventario_tipo",
        ),
        CheckConstraint(
            "cantidad_fisica <> 0 "
            "OR cantidad_reservada <> 0",
            name="ck_movimiento_inventario_cambio",
        ),
        CheckConstraint(
            "stock_fisico_anterior >= 0",
            name="ck_movimiento_stock_fisico_anterior",
        ),
        CheckConstraint(
            "stock_fisico_resultante >= 0",
            name="ck_movimiento_stock_fisico_resultante",
        ),
        CheckConstraint(
            "stock_reservado_anterior >= 0",
            name="ck_movimiento_stock_reservado_anterior",
        ),
        CheckConstraint(
            "stock_reservado_resultante >= 0",
            name="ck_movimiento_stock_reservado_resultante",
        ),
        CheckConstraint(
            "stock_reservado_anterior "
            "<= stock_fisico_anterior",
            name="ck_movimiento_stock_anterior_consistente",
        ),
        CheckConstraint(
            "stock_reservado_resultante "
            "<= stock_fisico_resultante",
            name="ck_movimiento_stock_resultante_consistente",
        ),
        CheckConstraint(
            "stock_fisico_resultante = "
            "stock_fisico_anterior + cantidad_fisica",
            name="ck_movimiento_cambio_fisico",
        ),
        CheckConstraint(
            "stock_reservado_resultante = "
            "stock_reservado_anterior + cantidad_reservada",
            name="ck_movimiento_cambio_reservado",
        ),
        CheckConstraint(
            "btrim(motivo) <> ''",
            name="ck_movimiento_inventario_motivo",
        ),
    )

    id: Mapped[UUID] = mapped_column(
        primary_key=True,
        default=uuid4,
    )

    inventario_sucursal_id: Mapped[UUID] = mapped_column(
        ForeignKey(
            "inventario_sucursal.id",
            ondelete="RESTRICT",
        ),
        index=True,
    )

    usuario_id: Mapped[UUID | None] = mapped_column(
        ForeignKey(
            "usuario_interno.id",
            ondelete="RESTRICT",
        ),
        nullable=True,
        index=True,
    )

    tipo: Mapped[str] = mapped_column(
        String(50),
        index=True,
    )

    cantidad_fisica: Mapped[int] = mapped_column(
        Integer,
        default=0,
        server_default="0",
    )

    cantidad_reservada: Mapped[int] = mapped_column(
        Integer,
        default=0,
        server_default="0",
    )

    stock_fisico_anterior: Mapped[int] = mapped_column(
        Integer,
    )

    stock_fisico_resultante: Mapped[int] = mapped_column(
        Integer,
    )

    stock_reservado_anterior: Mapped[int] = mapped_column(
        Integer,
    )

    stock_reservado_resultante: Mapped[int] = mapped_column(
        Integer,
    )

    motivo: Mapped[str] = mapped_column(
        String(250),
    )

    referencia_tipo: Mapped[str | None] = mapped_column(
        String(60),
        nullable=True,
    )

    referencia_id: Mapped[UUID | None] = mapped_column(
        nullable=True,
    )

    creado_en: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        index=True,
    )

    inventario: Mapped["InventarioSucursal"] = relationship(
        back_populates="movimientos",
        lazy="joined",
    )

    usuario: Mapped[UsuarioInterno | None] = relationship(
        lazy="joined",
    )

    @property
    def stock_disponible_anterior(self) -> int:
        return (
            self.stock_fisico_anterior
            - self.stock_reservado_anterior
        )

    @property
    def stock_disponible_resultante(self) -> int:
        return (
            self.stock_fisico_resultante
            - self.stock_reservado_resultante
        )


class RecepcionMercaderia(Base):
    __tablename__ = "recepcion_mercaderia"
    __table_args__ = (
        CheckConstraint("btrim(proveedor) <> ''", name="ck_recepcion_proveedor"),
        CheckConstraint("tipo_documento IN ('GUIA', 'FACTURA')", name="ck_recepcion_tipo_documento"),
        CheckConstraint("btrim(numero_documento) <> ''", name="ck_recepcion_documento"),
    )

    # El cliente conserva este UUID al reintentar una misma entrada.
    id: Mapped[UUID] = mapped_column(primary_key=True)
    solicitud_hash: Mapped[str] = mapped_column(String(64))
    sucursal_id: Mapped[UUID] = mapped_column(ForeignKey("sucursal.id", ondelete="RESTRICT"), index=True)
    usuario_id: Mapped[UUID] = mapped_column(ForeignKey("usuario_interno.id", ondelete="RESTRICT"), index=True)
    proveedor: Mapped[str] = mapped_column(String(150))
    tipo_documento: Mapped[str] = mapped_column(String(20))
    numero_documento: Mapped[str] = mapped_column(String(80))
    fecha_documento: Mapped[date] = mapped_column(Date)
    creado_en: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    detalles: Mapped[list["RecepcionMercaderiaDetalle"]] = relationship(
        passive_deletes="all", order_by="RecepcionMercaderiaDetalle.id",
    )


class RecepcionMercaderiaDetalle(Base):
    __tablename__ = "recepcion_mercaderia_detalle"
    __table_args__ = (
        CheckConstraint("cantidad > 0", name="ck_recepcion_detalle_cantidad"),
        UniqueConstraint("recepcion_id", "lote_id", name="uq_recepcion_detalle_lote"),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    recepcion_id: Mapped[UUID] = mapped_column(ForeignKey("recepcion_mercaderia.id", ondelete="RESTRICT"), index=True)
    lote_id: Mapped[UUID] = mapped_column(ForeignKey("lote_inventario.id", ondelete="RESTRICT"), index=True)
    cantidad: Mapped[int] = mapped_column(Integer)
    lote: Mapped["LoteInventario"] = relationship()


class AjusteInventario(Base):
    __tablename__ = "ajuste_inventario"
    __table_args__ = (CheckConstraint("btrim(motivo) <> ''", name="ck_ajuste_motivo"),)

    id: Mapped[UUID] = mapped_column(primary_key=True)
    solicitud_hash: Mapped[str] = mapped_column(String(64))
    sucursal_id: Mapped[UUID] = mapped_column(ForeignKey("sucursal.id", ondelete="RESTRICT"), index=True)
    usuario_id: Mapped[UUID] = mapped_column(ForeignKey("usuario_interno.id", ondelete="RESTRICT"), index=True)
    motivo: Mapped[str] = mapped_column(String(250))
    creado_en: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    detalles: Mapped[list["AjusteInventarioDetalle"]] = relationship(
        passive_deletes="all", order_by="AjusteInventarioDetalle.lote_id",
    )


class AjusteInventarioDetalle(Base):
    __tablename__ = "ajuste_inventario_detalle"
    __table_args__ = (
        UniqueConstraint("ajuste_id", "lote_id", name="uq_ajuste_lote"),
        CheckConstraint("cantidad_anterior >= 0 AND cantidad_nueva >= 0", name="ck_ajuste_cantidades"),
        CheckConstraint("cantidad_anterior <> cantidad_nueva", name="ck_ajuste_cambio"),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    ajuste_id: Mapped[UUID] = mapped_column(ForeignKey("ajuste_inventario.id", ondelete="RESTRICT"), index=True)
    lote_id: Mapped[UUID] = mapped_column(ForeignKey("lote_inventario.id", ondelete="RESTRICT"), index=True)
    cantidad_anterior: Mapped[int] = mapped_column(Integer)
    cantidad_nueva: Mapped[int] = mapped_column(Integer)
    lote: Mapped["LoteInventario"] = relationship()


class Transferencia(Base):
    __tablename__ = "transferencia"
    __table_args__ = (
        CheckConstraint("origen_id <> destino_id", name="ck_transferencia_sucursales"),
        CheckConstraint("estado IN ('SOLICITADA','AUTORIZADA','EN_TRANSITO','RECIBIDA','RECHAZADA')", name="ck_transferencia_estado"),
    )
    id: Mapped[UUID] = mapped_column(primary_key=True)
    solicitud_hash: Mapped[str] = mapped_column(String(64))
    origen_id: Mapped[UUID] = mapped_column(ForeignKey("sucursal.id", ondelete="RESTRICT"), index=True)
    destino_id: Mapped[UUID] = mapped_column(ForeignKey("sucursal.id", ondelete="RESTRICT"), index=True)
    estado: Mapped[str] = mapped_column(String(20), index=True)
    solicitante_id: Mapped[UUID] = mapped_column(ForeignKey("usuario_interno.id", ondelete="RESTRICT"))
    autorizador_id: Mapped[UUID | None] = mapped_column(ForeignKey("usuario_interno.id", ondelete="RESTRICT"))
    despachador_id: Mapped[UUID | None] = mapped_column(ForeignKey("usuario_interno.id", ondelete="RESTRICT"))
    receptor_id: Mapped[UUID | None] = mapped_column(ForeignKey("usuario_interno.id", ondelete="RESTRICT"))
    rechazada_por_id: Mapped[UUID | None] = mapped_column(ForeignKey("usuario_interno.id", ondelete="RESTRICT"))
    solicitada_en: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), index=True)
    autorizada_en: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    despachada_en: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    recibida_en: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    rechazada_en: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    motivo_rechazo: Mapped[str | None] = mapped_column(String(250))
    origen: Mapped["Sucursal"] = relationship(foreign_keys=[origen_id])
    destino: Mapped["Sucursal"] = relationship(foreign_keys=[destino_id])
    solicitante: Mapped["UsuarioInterno"] = relationship(foreign_keys=[solicitante_id])
    detalles: Mapped[list["TransferenciaDetalle"]] = relationship(passive_deletes="all", order_by="TransferenciaDetalle.producto_id")


class TransferenciaDetalle(Base):
    __tablename__ = "transferencia_detalle"
    __table_args__ = (
        UniqueConstraint("transferencia_id", "producto_id", name="uq_transferencia_producto"),
        CheckConstraint("cantidad > 0", name="ck_transferencia_detalle_cantidad"),
    )
    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    transferencia_id: Mapped[UUID] = mapped_column(ForeignKey("transferencia.id", ondelete="RESTRICT"), index=True)
    producto_id: Mapped[UUID] = mapped_column(ForeignKey("producto.id", ondelete="RESTRICT"), index=True)
    cantidad: Mapped[int] = mapped_column(Integer)
    producto: Mapped["Producto"] = relationship()
    lotes: Mapped[list["TransferenciaLote"]] = relationship(passive_deletes="all", order_by="TransferenciaLote.id")


class TransferenciaLote(Base):
    __tablename__ = "transferencia_lote"
    __table_args__ = (
        UniqueConstraint("detalle_id", "lote_origen_id", name="uq_transferencia_detalle_lote"),
        CheckConstraint("cantidad > 0", name="ck_transferencia_lote_cantidad"),
    )
    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    detalle_id: Mapped[UUID] = mapped_column(ForeignKey("transferencia_detalle.id", ondelete="RESTRICT"), index=True)
    lote_origen_id: Mapped[UUID] = mapped_column(ForeignKey("lote_inventario.id", ondelete="RESTRICT"), index=True)
    lote_destino_id: Mapped[UUID | None] = mapped_column(ForeignKey("lote_inventario.id", ondelete="RESTRICT"), index=True)
    cantidad: Mapped[int] = mapped_column(Integer)
    lote_origen: Mapped["LoteInventario"] = relationship(foreign_keys=[lote_origen_id])

class EventoAuditoria(Base):
    __tablename__ = "evento_auditoria"
    __table_args__ = (
        UniqueConstraint(
            "secuencia",
            name="uq_evento_auditoria_secuencia",
        ),
        CheckConstraint(
            "btrim(origen_actor) <> ''",
            name="ck_auditoria_origen",
        ),
        CheckConstraint(
            "btrim(accion) <> ''",
            name="ck_auditoria_accion",
        ),
        CheckConstraint(
            "btrim(referencia_historica) <> ''",
            name="ck_auditoria_referencia",
        ),
        CheckConstraint(
            "jsonb_typeof(datos_cambio) = 'object'",
            name="ck_auditoria_datos_objeto",
        ),
        Index(
            "ix_auditoria_producto_secuencia",
            "producto_id",
            "secuencia",
        ),
        Index("ix_auditoria_usuario", "usuario_id"),
        Index("ix_auditoria_sucursal", "sucursal_id"),
    )

    id: Mapped[UUID] = mapped_column(
        primary_key=True,
        default=uuid4,
    )

    secuencia: Mapped[int] = mapped_column(
        BigInteger,
        Identity(always=True),
        nullable=False,
    )

    ocurrido_en: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    origen_actor: Mapped[str] = mapped_column(String(40))
    accion: Mapped[str] = mapped_column(String(100))
    referencia_historica: Mapped[str] = mapped_column(Text)
    datos_cambio: Mapped[dict[str, object]] = mapped_column(JSONB)

    usuario_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("usuario_interno.id", ondelete="RESTRICT"),
        nullable=True,
    )

    sucursal_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("sucursal.id", ondelete="RESTRICT"),
        nullable=True,
    )

    producto_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("producto.id", ondelete="RESTRICT"),
        nullable=True,
    )


class VinculacionScanner(Base):
    """E8-H1: conexión temporal entre una pantalla POS y el móvil."""

    __tablename__ = "vinculacion_scanner"
    __table_args__ = (
        UniqueConstraint(
            "codigo_hash",
            name="uq_scanner_codigo_hash",
        ),
        CheckConstraint(
            "qr_expira_en > creada_en AND expira_en >= qr_expira_en",
            name="ck_scanner_expiracion",
        ),
        CheckConstraint(
            "(vinculada_en IS NULL AND sesion_movil_id IS NULL) OR "
            "(vinculada_en IS NOT NULL AND sesion_movil_id IS NOT NULL "
            "AND vinculada_en >= creada_en AND vinculada_en < qr_expira_en)",
            name="ck_scanner_vinculacion",
        ),
        CheckConstraint(
            "revocada_en IS NULL OR revocada_en >= creada_en",
            name="ck_scanner_revocacion",
        ),
        CheckConstraint(
            "sesion_movil_id IS NULL OR sesion_movil_id <> sesion_web_id",
            name="ck_scanner_sesiones_distintas",
        ),
        Index("ix_scanner_caja", "sesion_caja_id"),
        Index("ix_scanner_sesion_web", "sesion_web_id"),
        Index("ix_scanner_sesion_movil", "sesion_movil_id"),
    )

    id: Mapped[UUID] = mapped_column(
        primary_key=True,
        default=uuid4,
    )
    usuario_id: Mapped[UUID] = mapped_column(
        ForeignKey("usuario_interno.id", ondelete="RESTRICT"),
    )
    sucursal_id: Mapped[UUID] = mapped_column(
        ForeignKey("sucursal.id", ondelete="RESTRICT"),
    )
    sesion_caja_id: Mapped[UUID] = mapped_column(
        ForeignKey("sesion_caja.id", ondelete="RESTRICT"),
    )
    sesion_web_id: Mapped[UUID] = mapped_column(
        ForeignKey("sesion_interna.id", ondelete="RESTRICT"),
    )
    sesion_movil_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("sesion_interna.id", ondelete="RESTRICT"),
    )
    codigo_hash: Mapped[str] = mapped_column(
        String(64),
    )
    creada_en: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
    )
    qr_expira_en: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
    )
    expira_en: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
    )
    vinculada_en: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
    )
    revocada_en: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
    )