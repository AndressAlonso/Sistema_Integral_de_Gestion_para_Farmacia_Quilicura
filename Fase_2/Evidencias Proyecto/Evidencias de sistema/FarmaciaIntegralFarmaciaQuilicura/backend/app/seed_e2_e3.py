"""Integración E2-H1/E3-H1: incorpora permisos sin restablecer roles editados."""

from sqlalchemy import select, text
from sqlalchemy.orm import Session

from app.models import Permiso
from app.role_catalog import ADMIN_ROLE, sync_roles


def seed_permissions(db: Session) -> None:
    db.execute(text("SELECT pg_advisory_xact_lock(184701)"))
    db.execute(text("SELECT pg_advisory_xact_lock(73412002)"))
    first_catalog_install = db.scalar(
        select(Permiso.id).where(Permiso.codigo == "catalogo.gestionar")
    ) is None
    roles = sync_roles(db)
    if first_catalog_install:
        permission = db.scalar(
            select(Permiso).where(Permiso.codigo == "catalogo.gestionar")
        )
        admin = roles[ADMIN_ROLE]
        if permission not in admin.permisos:
            admin.permisos.append(permission)
    db.flush()


def main() -> None:
    from app.db import create_database_engine, create_session_factory

    engine = create_database_engine()
    try:
        with create_session_factory(engine).begin() as db:
            seed_permissions(db)
        print("Permisos E2/E3 sincronizados; usuarios y configuración existente conservados.")
    finally:
        engine.dispose()


if __name__ == "__main__":
    main()
