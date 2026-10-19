"""Instalación E5; conserva permisos personalizados al volver a ejecutar."""

from sqlalchemy import select, text

from app.db import create_database_engine, create_session_factory
from app.models import Permiso
from app.role_catalog import sync_roles


def seed(db):
    db.execute(text("SELECT pg_advisory_xact_lock(184701)"))
    db.execute(text("SELECT pg_advisory_xact_lock(73412002)"))
    new = [
        code
        for code in ("pos.operar", "caja.operar", "ventas.reversar")
        if db.scalar(select(Permiso.id).where(Permiso.codigo == code)) is None
    ]
    roles = sync_roles(db)
    for code in new:
        permission = db.scalar(select(Permiso).where(Permiso.codigo == code))
        for role in ("ADMINISTRADOR", "VENDEDOR_CAJERO"):
            if code == "ventas.reversar" and role != "ADMINISTRADOR":
                continue
            if permission not in roles[role].permisos:
                roles[role].permisos.append(permission)


if __name__ == "__main__":
    engine = create_database_engine()
    try:
        with create_session_factory(engine).begin() as session:
            seed(session)
        print("Permisos E5 instalados; personalizaciones conservadas.")
    finally:
        engine.dispose()
