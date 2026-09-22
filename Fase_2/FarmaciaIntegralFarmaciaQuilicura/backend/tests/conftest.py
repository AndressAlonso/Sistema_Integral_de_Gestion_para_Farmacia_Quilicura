"""Pruebas PostgreSQL: solo DML en una transacción revertida por caso.

Requiere SIGFQ_TEST_ROLLBACK=1 y DB_* apuntando a una instancia local de desarrollo
con 0001_acceso aplicada. No crea bases, tablas ni modifica migraciones.
"""

import os
from types import SimpleNamespace
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import sessionmaker

from app.auth.security import password_hasher
from app.config import Settings
from app.db import create_database_engine
from app.main import create_app
from app.models import Permiso, Rol, Sucursal, UsuarioInterno

PASSWORD = "Solo-pruebas-E1H1-H2!"


@pytest.fixture(scope="session")
def password_hash():
    return password_hasher.hash(PASSWORD)


@pytest.fixture
def setup(password_hash):
    if os.environ.get("SIGFQ_TEST_ROLLBACK") != "1":
        pytest.skip(
            "Habilita SIGFQ_TEST_ROLLBACK=1 para probar PostgreSQL local con rollback"
        )
    engine = create_database_engine()
    with engine.connect() as connection:
        transaction = connection.begin()
        connection.exec_driver_sql("SET LOCAL lock_timeout = '5s'")
        factory = sessionmaker(
            bind=connection,
            expire_on_commit=False,
            join_transaction_mode="create_savepoint",
        )
        try:
            suffix = uuid4().hex
            ids = {
                name: uuid4()
                for name in (
                    "admin",
                    "operator",
                    "inactive",
                    "manager",
                    "branch",
                    "admin_role",
                    "operator_role",
                    "manager_role",
                )
            }
            emails = {
                name: f"test-{name}-{suffix}@farmacia.cl"
                for name in ("admin", "operator", "inactive", "manager")
            }
            with factory.begin() as db:
                permissions = {}
                for code in ("usuarios.gestionar", "roles.gestionar"):
                    permission = db.scalar(
                        select(Permiso).where(Permiso.codigo == code)
                    )
                    if permission is None:
                        permission = Permiso(
                            codigo=code, descripcion="Fixture temporal"
                        )
                        db.add(permission)
                    permissions[code] = permission
                branch = Sucursal(
                    id=ids["branch"],
                    codigo=f"T-{suffix[:20]}",
                    nombre="Sucursal de prueba temporal",
                    direccion_local="Ficticia",
                    activa=True,
                )
                admin = Rol(
                    id=ids["admin_role"],
                    codigo=f"TEST_ADMIN_{suffix}",
                    nombre="Administrador de prueba",
                    permisos=list(permissions.values()),
                )
                operator = Rol(
                    id=ids["operator_role"],
                    codigo=f"TEST_OPERADOR_{suffix}",
                    nombre="Operador de prueba",
                )
                manager = Rol(
                    id=ids["manager_role"],
                    codigo=f"TEST_GESTOR_{suffix}",
                    nombre="Gestor sin asignación de roles",
                    permisos=[permissions["usuarios.gestionar"]],
                )
                db.add_all([branch, admin, operator, manager])
                for name, role in (
                    ("admin", admin),
                    ("operator", operator),
                    ("inactive", operator),
                    ("manager", manager),
                ):
                    db.add(
                        UsuarioInterno(
                            id=ids[name],
                            nombre=f"Fixture {name}",
                            correo=emails[name],
                            password_hash=password_hash,
                            activo=name != "inactive",
                            sucursal=branch,
                            roles=[role],
                        )
                    )
            settings = Settings(_env_file=None, jwt_secret_key="test-only-" * 8)
            app = create_app(settings, session_factory=factory)
            with TestClient(app, raise_server_exceptions=False) as client:
                yield SimpleNamespace(
                    client=client,
                    app=app,
                    settings=settings,
                    factory=factory,
                    ids=ids,
                    emails=emails,
                    suffix=suffix,
                )
        finally:
            transaction.rollback()
    engine.dispose()
