"""E1-H3: catálogo acordado y carga idempotente sobre las tablas existentes."""

from dataclasses import dataclass

from sqlalchemy import select, text
from sqlalchemy.orm import Session

from app.models import Permiso, Rol

ADMIN_ROLE = "ADMINISTRADOR"


@dataclass(frozen=True)
class RoleDefinition:
    name: str
    description: str
    permissions: tuple[str, ...] = ()


ROLE_CATALOG = {
    ADMIN_ROLE: RoleDefinition(
        "Administrador",
        "Administración general del sistema: usuarios, roles, permisos, sucursales, "
        "catálogo, precios, promociones, configuraciones, autorizaciones, auditoría e indicadores.",
        (
            "usuarios.gestionar",
            "roles.gestionar",
            "sucursales.gestionar",
            "inventario.consultar",
            "inventario.gestionar_lotes",
            "inventario.registrar_entrada",
            "inventario.ajustar",
            "inventario.configurar_minimo",
            "catalogo.gestionar",
            "transferencias.consultar", "transferencias.solicitar", "transferencias.autorizar",
            "transferencias.despachar", "transferencias.recibir",
        ),
    ),
    "VENDEDOR_CAJERO": RoleDefinition(
        "Vendedor / Cajero",
        "Operación de POS, ventas, comprobantes, apertura y cierre de caja y escáner móvil de productos.",
    ),
    "ENCARGADO_INVENTARIO": RoleDefinition(
        "Encargado de inventario",
        "Stock, lotes, recepciones, transferencias, movimientos y ajustes de inventario.",
        ("inventario.consultar", "inventario.gestionar_lotes", "inventario.configurar_minimo", "inventario.registrar_entrada", "inventario.ajustar",
         "transferencias.consultar", "transferencias.solicitar", "transferencias.despachar", "transferencias.recibir"),
    ),
    "ENCARGADO_PEDIDOS": RoleDefinition(
        "Encargado de pedidos",
        "Preparación de pedidos online, seguimiento, cambio de estados y entrega mediante QR.",
    ),
    "QUIMICO_FARMACEUTICO": RoleDefinition(
        "Químico farmacéutico",
        "Acceso limitado al catálogo farmacéutico y autorización o marcado de productos sujetos a receta.",
    ),
    "SOCIO": RoleDefinition(
        "Socio", "Consulta de indicadores y auditoría, principalmente en modalidad lectura.",
    ),
}

# Solo permisos existentes. El alcance futuro no habilita módulos por adelantado.
PERMISSIONS = {
    "transferencias.consultar": ("Consultar transferencias de las sucursales autorizadas", True),
    "transferencias.solicitar": ("Solicitar transferencias con reserva de stock", True),
    "transferencias.autorizar": ("Aprobar o rechazar transferencias como administrador", True),
    "transferencias.despachar": ("Confirmar despacho desde la sucursal asignada", True),
    "transferencias.recibir": ("Confirmar recepción en la sucursal asignada", True),
    "usuarios.gestionar": ("Gestionar usuarios internos", True),
    "roles.gestionar": ("Crear, configurar y asignar roles", True),
    "sucursales.gestionar": ("Gestionar sucursales", True),
    "inventario.consultar": ("Consultar inventario", True),
    "inventario.gestionar_lotes": ("Gestionar lotes y fechas de vencimiento", True),
    "inventario.registrar_entrada": ("Registrar entradas de mercadería con respaldo", True),
    "inventario.ajustar": ("Ajustar cantidades por lote con motivo y trazabilidad", True),
    "inventario.configurar_minimo": ("Configurar stock mínimo por producto y sucursal", True),
    "catalogo.gestionar": ("Gestionar productos y categorías", True),
}


def sync_roles(db: Session) -> dict[str, Rol]:
    """No hace commit: el llamador controla la transacción completa."""
    db.execute(text("SELECT pg_advisory_xact_lock(184701)"))
    db.execute(text("SELECT pg_advisory_xact_lock(73412002)"))
    for old, new in (("ADMIN", ADMIN_ROLE), ("OPERADOR", "ENCARGADO_INVENTARIO")):
        legacy = db.scalar(select(Rol).where(Rol.codigo == old))
        current = db.scalar(select(Rol).where(Rol.codigo == new))
        if legacy is not None and current is not None:
            raise ValueError(f"Existen {old} y {new}; revisa sus asignaciones antes de continuar.")
        if legacy is not None:
            legacy.codigo = new
    db.flush()

    permissions = {}
    for code, (description, _) in PERMISSIONS.items():
        permission = db.scalar(select(Permiso).where(Permiso.codigo == code))
        if permission is None:
            permission = Permiso(codigo=code, descripcion=description)
            db.add(permission)
        permissions[code] = permission

    roles = {}
    for code, definition in ROLE_CATALOG.items():
        role = db.scalar(select(Rol).where(Rol.codigo == code))
        if role is None:
            role = Rol(
                codigo=code, nombre=definition.name,
                permisos=[permissions[key] for key in definition.permissions],
            )
            db.add(role)
        roles[code] = role
    db.flush()
    return roles


def main() -> None:
    from app.db import create_database_engine, create_session_factory

    engine = create_database_engine()
    try:
        with create_session_factory(engine).begin() as db:
            sync_roles(db)
        print("Seis roles configurados. UUID y asignaciones existentes conservados.")
    finally:
        engine.dispose()


if __name__ == "__main__":
    main()
