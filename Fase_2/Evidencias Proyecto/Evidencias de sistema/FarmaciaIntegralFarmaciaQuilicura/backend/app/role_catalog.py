"""E1-H3: catálogo acordado y carga idempotente sobre las tablas existentes."""

import argparse
import sys
from dataclasses import dataclass

from sqlalchemy import select, text
from sqlalchemy.exc import SQLAlchemyError
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


E4_PERMISSIONS = (
    "transferencias.consultar", "transferencias.solicitar",
    "transferencias.autorizar", "transferencias.despachar",
    "transferencias.recibir", "inventario.registrar_entrada", "inventario.ajustar",
)
E4_ROLE_PERMISSIONS = {
    ADMIN_ROLE: E4_PERMISSIONS,
    "ENCARGADO_INVENTARIO": tuple(
        code for code in E4_PERMISSIONS if code != "transferencias.autorizar"
    ),
}


def reconcile_e4_permissions(db: Session) -> dict:
    """Completa solo E4; el llamador controla commit y rollback."""
    db.execute(text("SELECT pg_advisory_xact_lock(184701)"))
    db.execute(text("SELECT pg_advisory_xact_lock(73412002)"))
    roles = {}
    for code in E4_ROLE_PERMISSIONS:
        role = db.scalar(select(Rol).where(Rol.codigo == code))
        if role is None:
            role = Rol(codigo=code, nombre=ROLE_CATALOG[code].name, permisos=[])
            db.add(role)
        roles[code] = role
    worker = roles["ENCARGADO_INVENTARIO"]
    if any(p.codigo == "transferencias.autorizar" for p in worker.permisos):
        raise ValueError(
            "Conflicto: ENCARGADO_INVENTARIO tiene transferencias.autorizar. "
            "No se eliminará la asignación automáticamente."
        )

    created = []
    permissions = {}
    for code in E4_PERMISSIONS:
        permission = db.scalar(select(Permiso).where(Permiso.codigo == code))
        if permission is None:
            permission = Permiso(codigo=code, descripcion=PERMISSIONS[code][0])
            db.add(permission)
            created.append(code)
        permissions[code] = permission

    added = {}
    for code, required in E4_ROLE_PERMISSIONS.items():
        existing = {p.codigo for p in roles[code].permisos}
        added[code] = []
        for permission_code in required:
            if permission_code not in existing:
                roles[code].permisos.append(permissions[permission_code])
                existing.add(permission_code)
                added[code].append(permission_code)
    db.flush()
    for code, required in E4_ROLE_PERMISSIONS.items():
        db.expire(roles[code], ["permisos"])
        actual = [p.codigo for p in roles[code].permisos]
        if not set(required).issubset(actual) or len(actual) != len(set(actual)):
            raise ValueError(f"Verificación de permisos E4 fallida para {code}.")
        if code == "ENCARGADO_INVENTARIO" and "transferencias.autorizar" in actual:
            raise ValueError("Conflicto: ENCARGADO_INVENTARIO tiene transferencias.autorizar.")
    return {"permissions_created": created, "links_added": added}


def _snapshot(db: Session) -> tuple[set[str], dict[str, set[str]]]:
    permissions = {p.codigo for p in db.scalars(select(Permiso))}
    links = {code: set() for code in E4_ROLE_PERMISSIONS}
    legacy_codes = {"ADMIN": ADMIN_ROLE, "OPERADOR": "ENCARGADO_INVENTARIO"}
    for role in db.scalars(select(Rol)):
        code = legacy_codes.get(role.codigo, role.codigo)
        if code in links:
            links[code].update(p.codigo for p in role.permisos)
    return permissions, links


def main(argv: list[str] | None = None) -> int:
    from app.db import create_database_engine, create_session_factory

    parser = argparse.ArgumentParser(description="Configuración de roles SIGFQ")
    parser.add_argument("--reconcile-e4", action="store_true",
                        help="Completar aditivamente los permisos obligatorios de E4")
    args = parser.parse_args(argv)
    engine = create_database_engine()
    try:
        with create_session_factory(engine).begin() as db:
            if args.reconcile_e4:
                db.execute(text("SELECT pg_advisory_xact_lock(184701)"))
                db.execute(text("SELECT pg_advisory_xact_lock(73412002)"))
                before_permissions, before_links = _snapshot(db)
            sync_roles(db)
            if args.reconcile_e4:
                reconcile_e4_permissions(db)
                after_permissions, after_links = _snapshot(db)
                created = sorted(after_permissions - before_permissions)
                added = {
                    code: sorted((after_links[code] - before_links[code]) & set(required))
                    for code, required in E4_ROLE_PERMISSIONS.items()
                }
        if args.reconcile_e4:
            print(f"Permisos creados ({len(created)}): {', '.join(created) or 'ninguno'}.")
            for code, codes in added.items():
                print(f"Vínculos agregados para {code} ({len(codes)}): "
                      f"{', '.join(codes) or 'ninguno'}.")
            if not created and not any(added.values()):
                print("Idempotencia confirmada: sin incorporaciones de permisos o vínculos E4.")
            print("Commit confirmado: catálogo y matriz E4 verificados en una única transacción.")
        else:
            print("Seis roles configurados. UUID y asignaciones existentes conservados.")
        return 0
    except (ValueError, SQLAlchemyError) as exc:
        message = str(exc) if isinstance(exc, ValueError) else "No se pudo completar la configuración."
        print(f"Rollback: {message} No se confirmaron cambios parciales.", file=sys.stderr)
        return 1
    finally:
        engine.dispose()


if __name__ == "__main__":
    raise SystemExit(main())
