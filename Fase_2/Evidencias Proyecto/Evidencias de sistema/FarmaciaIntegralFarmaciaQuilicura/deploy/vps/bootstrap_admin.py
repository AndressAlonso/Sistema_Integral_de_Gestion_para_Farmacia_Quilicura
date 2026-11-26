"""Carga inicial explícita: un administrador y dos sucursales, sin usuarios demo."""
from getpass import getpass

from sqlalchemy import func, select, text

from app.auth.security import password_hasher
from app.db import create_database_engine, create_session_factory
from app.models import Sucursal, UsuarioInterno
from app.role_catalog import sync_roles


def main():
    password = getpass("Contraseña nueva para interno@farmacia.cl (mínimo 12): ")
    if len(password) < 12 or password != getpass("Repite la contraseña: "):
        raise SystemExit("Contraseña corta o distinta. No se cambió nada.")
    engine = create_database_engine()
    try:
        with create_session_factory(engine).begin() as db:
            db.execute(text("SELECT pg_advisory_xact_lock(184701)"))
            if db.scalar(select(func.count()).select_from(UsuarioInterno)):
                raise SystemExit("Ya existen usuarios internos. No se modificó ninguna cuenta.")
            branches = []
            for code, name in (("LOCAL-01", "Sucursal Quilicura"), ("LOCAL-02", "Sucursal Norte")):
                branch = db.scalar(select(Sucursal).where(Sucursal.codigo == code))
                if branch is None:
                    branch = Sucursal(codigo=code, nombre=name, direccion_local="Dirección de prueba", activa=True)
                    db.add(branch)
                    db.flush()
                branches.append(branch)
            roles = sync_roles(db)
            db.add(UsuarioInterno(correo="interno@farmacia.cl", nombre="Administrador SIGFQ",
                password_hash=password_hasher.hash(password), activo=True,
                sucursal_id=branches[0].id, roles=[roles["ADMINISTRADOR"]]))
        print("OK: administrador creado. Configura las direcciones reales desde Sucursales.")
    finally:
        engine.dispose()


if __name__ == "__main__":
    main()
