"""Carga inicial local: crea faltantes y conserva registros existentes."""

import os

from sqlalchemy import select, text

from app.db import create_database_engine, create_session_factory
from app.models import Permiso, Rol, Sucursal, UsuarioInterno
from app.auth.security import password_hasher

CUENTAS = (
    ("interno@farmacia.cl", "Administrador de prueba", "ADMIN", True),
    ("operador@farmacia.cl", "Operador de prueba", "OPERADOR", True),
    ("inactivo@farmacia.cl", "Usuario inactivo de prueba", "OPERADOR", False),
)


def seed(db, password: str):
    if len(password) < 12:
        raise ValueError("DEMO_PASSWORD debe tener al menos 12 caracteres.")
    # Evita dos cargas iniciales simultáneas en la misma base.
    db.execute(text("SELECT pg_advisory_xact_lock(184701)"))
    sucursal = db.scalar(select(Sucursal).where(Sucursal.codigo == "LOCAL-01"))
    if sucursal is None:
        sucursal = Sucursal(
            codigo="LOCAL-01",
            nombre="Sucursal de prueba",
            direccion_local="Dirección ficticia",
            activa=True,
        )
        db.add(sucursal)
        db.flush()
    specs = [
        ("usuarios.gestionar", "Gestionar usuarios internos"),
        ("roles.gestionar", "Gestionar roles y permisos"),
        ("sucursales.gestionar", "Gestionar sucursales"),
        ("inventario.consultar", "Consultar inventario"),
    ]
    permisos = {}
    for codigo, descripcion in specs:
        permiso = db.scalar(select(Permiso).where(Permiso.codigo == codigo))
        if permiso is None:
            permiso = Permiso(codigo=codigo, descripcion=descripcion)
            db.add(permiso)
            db.flush()
        permisos[codigo] = permiso
    roles = {}
    for codigo, nombre, codigos in [
        ("ADMIN", "Administrador", list(permisos)),
        ("OPERADOR", "Operador", ["inventario.consultar"]),
    ]:
        rol = db.scalar(select(Rol).where(Rol.codigo == codigo))
        if rol is None:
            rol = Rol(codigo=codigo, nombre=nombre, permisos=[permisos[c] for c in codigos])
            db.add(rol)
            db.flush()
        roles[codigo] = rol
    creados = 0
    for correo, nombre, rol, activo in CUENTAS:
        if db.scalar(select(UsuarioInterno).where(UsuarioInterno.correo == correo)) is None:
            db.add(
                UsuarioInterno(
                    correo=correo,
                    nombre=nombre,
                    password_hash=password_hasher.hash(password),
                    activo=activo,
                    sucursal_id=sucursal.id,
                    roles=[roles[rol]],
                )
            )
            creados += 1
    db.commit()
    return creados


def main():
    if os.getenv("APP_ENV", "local") != "local":
        raise RuntimeError("La carga de cuentas ficticias solo está habilitada en APP_ENV=local.")
    password = os.environ.get("DEMO_PASSWORD", "")
    engine = create_database_engine()
    try:
        with create_session_factory(engine)() as db:
            print(
                f"Usuarios ficticios creados: {seed(db, password)}. Registros existentes conservados."
            )
    finally:
        engine.dispose()


if __name__ == "__main__":
    main()
