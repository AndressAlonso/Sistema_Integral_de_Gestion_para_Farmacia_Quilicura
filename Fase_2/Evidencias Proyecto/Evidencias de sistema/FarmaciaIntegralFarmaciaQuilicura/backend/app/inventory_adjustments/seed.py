"""Instala E4-H5 sin restablecer permisos personalizados."""

from sqlalchemy import select, text

from app.db import create_database_engine, create_session_factory
from app.inventory_adjustments.service import PERMISSION
from app.models import Permiso
from app.role_catalog import ADMIN_ROLE, sync_roles


def seed(db):
    db.execute(text("SELECT pg_advisory_xact_lock(184701)"))
    db.execute(text("SELECT pg_advisory_xact_lock(73412002)"))
    is_new = db.scalar(select(Permiso.id).where(Permiso.codigo == PERMISSION)) is None
    roles = sync_roles(db)
    if is_new:
        permission = db.scalar(select(Permiso).where(Permiso.codigo == PERMISSION))
        for code in (ADMIN_ROLE, "ENCARGADO_INVENTARIO"):
            if permission not in roles[code].permisos:
                roles[code].permisos.append(permission)
    db.flush()


def main():
    engine = create_database_engine()
    try:
        with create_session_factory(engine).begin() as db:
            seed(db)
        print("Permiso de ajustes instalado; personalizaciones conservadas.")
    finally:
        engine.dispose()


if __name__ == "__main__":
    main()
