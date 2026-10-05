"""Carga E4-H1/H2/H3: solo asigna permisos nuevos en su primera instalación."""

from sqlalchemy import select, text

from app.db import create_database_engine, create_session_factory
from app.models import Permiso
from app.role_catalog import ADMIN_ROLE, PERMISSIONS, ROLE_CATALOG, sync_roles


def seed(db):
    db.execute(text("SELECT pg_advisory_xact_lock(184701)"))
    db.execute(text("SELECT pg_advisory_xact_lock(73412002)"))
    existing = set(db.scalars(select(Permiso.codigo)))
    new = {
        code
        for code in PERMISSIONS
        if code.startswith("transferencias.") and code not in existing
    }
    roles = sync_roles(db)
    for code in (ADMIN_ROLE, "ENCARGADO_INVENTARIO"):
        for permission_code in ROLE_CATALOG[code].permissions:
            if permission_code in new:
                permission = db.scalar(
                    select(Permiso).where(Permiso.codigo == permission_code)
                )
                if permission not in roles[code].permisos:
                    roles[code].permisos.append(permission)
    db.flush()


def main():
    engine = create_database_engine()
    try:
        with create_session_factory(engine).begin() as db:
            seed(db)
        print(
            "Permisos de transferencias instalados; personalizaciones existentes conservadas."
        )
    finally:
        engine.dispose()


if __name__ == "__main__":
    main()
