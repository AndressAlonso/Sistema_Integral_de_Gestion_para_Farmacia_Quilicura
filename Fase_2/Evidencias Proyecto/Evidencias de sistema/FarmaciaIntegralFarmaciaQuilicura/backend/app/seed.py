"""Carga inicial local: crea faltantes y conserva registros existentes."""

import os

from sqlalchemy import select, text

from app.auth.security import password_hasher
from app.db import create_database_engine, create_session_factory
from app.models import Sucursal, UsuarioInterno
from app.role_catalog import sync_roles

SUCURSALES = (
    (
        "LOCAL-01",
        "Sucursal Quilicura",
        "Avenida principal 100, Quilicura",
        True,
    ),
    (
        "LOCAL-02",
        "Sucursal Norte",
        "Avenida norte 200, Quilicura",
        False,
    ),
)

CUENTAS = (
    (
        "interno@farmacia.cl",
        "Administrador de prueba",
        "ADMINISTRADOR",
        True,
    ),
    (
        "operador@farmacia.cl",
        "Operador de prueba",
        "ENCARGADO_INVENTARIO",
        True,
    ),
    (
        "inactivo@farmacia.cl",
        "Usuario inactivo de prueba",
        "ENCARGADO_INVENTARIO",
        False,
    ),
)

def seed(db, password: str) -> int:
    if len(password) < 12:
        raise ValueError(
            "DEMO_PASSWORD debe tener al menos 12 caracteres."
        )

    # Evita dos cargas iniciales simultáneas en la misma base.
    db.execute(
        text("SELECT pg_advisory_xact_lock(184701)")
    )

    sucursales = {}

    for codigo, nombre, direccion, activa in SUCURSALES:
        sucursal = db.scalar(
            select(Sucursal).where(
                Sucursal.codigo == codigo
            )
        )

        if sucursal is None:
            sucursal = Sucursal(
                codigo=codigo,
                nombre=nombre,
                direccion_local=direccion,
                activa=activa,
            )
            db.add(sucursal)
            db.flush()

        sucursales[codigo] = sucursal

    roles = sync_roles(db)

    sucursal_principal = sucursales["LOCAL-01"]
    creados = 0

    for correo, nombre, codigo_rol, activo in CUENTAS:
        usuario = db.scalar(
            select(UsuarioInterno).where(
                UsuarioInterno.correo == correo
            )
        )

        if usuario is None:
            db.add(
                UsuarioInterno(
                    correo=correo,
                    nombre=nombre,
                    password_hash=password_hasher.hash(
                        password
                    ),
                    activo=activo,
                    sucursal_id=sucursal_principal.id,
                    roles=[
                        roles[codigo_rol],
                    ],
                )
            )
            creados += 1

    db.commit()

    return creados


def main():
    if os.getenv("APP_ENV", "local") != "local":
        raise RuntimeError(
            "La carga de cuentas ficticias solo está "
            "habilitada en APP_ENV=local."
        )

    password = os.environ.get(
        "DEMO_PASSWORD",
        "",
    )

    engine = create_database_engine()

    try:
        with create_session_factory(engine)() as db:
            usuarios_creados = seed(
                db,
                password,
            )

            print(
                "Usuarios ficticios creados: "
                f"{usuarios_creados}. "
                "Registros existentes conservados."
            )
    finally:
        engine.dispose()


if __name__ == "__main__":
    main()