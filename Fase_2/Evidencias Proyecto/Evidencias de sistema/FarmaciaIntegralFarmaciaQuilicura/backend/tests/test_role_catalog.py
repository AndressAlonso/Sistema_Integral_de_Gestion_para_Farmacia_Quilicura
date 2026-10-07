from copy import deepcopy
from unittest.mock import Mock
from uuid import uuid4

import pytest
from app.models import Permiso, Rol, UsuarioInterno
from app.role_catalog import (
    ADMIN_ROLE,
    E4_PERMISSIONS,
    E4_ROLE_PERMISSIONS,
    PERMISSIONS,
    ROLE_CATALOG,
    main,
    reconcile_e4_permissions,
    sync_roles,
)
from sqlalchemy import select
from test_auth import login
from test_users import payload


def test_role_sync_preserves_ids_assignments_and_is_repeatable(setup):
    with setup.factory.begin() as db:
        # Trabaja en la transacción de fixture; los datos reales se revierten.
        for old, new in (("ADMIN", ADMIN_ROLE), ("OPERADOR", "ENCARGADO_INVENTARIO")):
            role = db.scalar(select(Rol).where(Rol.codigo == new))
            legacy = db.scalar(select(Rol).where(Rol.codigo == old))
            if role is not None and legacy is None:
                role.codigo = old
        db.flush()
        before = {role.codigo: role.id for role in db.scalars(select(Rol))}
        users_before = {user.id: {role.id for role in user.roles}
                        for user in db.scalars(select(UsuarioInterno))}
        first = {code: role.id for code, role in sync_roles(db).items()}
        second = {code: role.id for code, role in sync_roles(db).items()}
        assert first == second
        if "ADMIN" in before:
            assert first[ADMIN_ROLE] == before["ADMIN"]
        if "OPERADOR" in before:
            assert first["ENCARGADO_INVENTARIO"] == before["OPERADOR"]
        assert not db.scalar(select(Rol).where(Rol.codigo.in_(["ADMIN", "OPERADOR"])))
        for user in db.scalars(select(UsuarioInterno)):
            assert {role.id for role in user.roles} == users_before[user.id]


@pytest.mark.parametrize("role_code", list(ROLE_CATALOG))
def test_roles_can_be_assigned_and_permissions_are_enforced(setup, role_code):
    with setup.factory.begin() as db:
        roles = sync_roles(db)
        role_id = str(roles[role_code].id)
        expected = sorted(permission.codigo for permission in roles[role_code].permisos)
    login(setup)
    options = setup.client.get('/api/users').json()['roles']
    option = next(role for role in options if role['code'] == role_code)
    assert option['description'] == ROLE_CATALOG[role_code].description
    assert sorted(permission['code'] for permission in option['permissions']) == expected
    created = setup.client.post('/api/users', json=payload(setup, role_ids=[role_id]))
    assert created.status_code == 201
    assert created.json()['roles'] == [role_code]
    assert created.json()['permissions'] == expected
    from conftest import PASSWORD
    assert setup.client.post('/api/auth/login', json={
        'email': created.json()['email'], 'password': PASSWORD,
    }).status_code == 200
    assert setup.client.get('/api/auth/me').json()['user']['permissions'] == expected
    assert setup.client.get('/api/auth/me').json()['user']['roles'] == [role_code]
    assert setup.client.get('/api/users').status_code == (200 if 'usuarios.gestionar' in expected else 403)


def test_sync_conflicting_legacy_role_does_not_merge_silently(setup):
    with setup.factory.begin() as db:
        sync_roles(db)
        db.add(Rol(codigo='OPERADOR', nombre='Operador legado'))
        db.flush()
        with pytest.raises(ValueError, match='Existen OPERADOR'):
            sync_roles(db)


class MemoryCatalog:
    """Doble limitado del catálogo; no abre conexiones ni usa SQLite."""

    def __init__(self):
        self.roles = []
        self.permissions = []
        self.user_roles = {(uuid4(), uuid4())}
        self.users = {"unchanged": ("password-hash", "session-token")}
        self.commits = 0
        self.rollbacks = 0

    def execute(self, statement):
        assert "pg_advisory_xact_lock" in str(statement)

    def scalar(self, statement):
        entity = statement.column_descriptions[0]["entity"]
        code = next(iter(statement.compile().params.values()))
        rows = self.roles if entity is Rol else self.permissions
        return next((row for row in rows if row.codigo == code), None)

    def scalars(self, statement):
        entity = statement.column_descriptions[0]["entity"]
        return list(self.roles if entity is Rol else self.permissions)

    def add(self, row):
        row.id = row.id or uuid4()
        (self.roles if isinstance(row, Rol) else self.permissions).append(row)

    def flush(self):
        assert len({p.codigo for p in self.permissions}) == len(self.permissions)
        assert len({r.codigo for r in self.roles}) == len(self.roles)
        for role in self.roles:
            assert len({p.codigo for p in role.permisos}) == len(role.permisos)

    def expire(self, role, fields):
        assert role in self.roles and fields == ["permisos"]

    def begin(self):
        catalog = self

        class Transaction:
            def __enter__(self):
                self.before = deepcopy((catalog.roles, catalog.permissions,
                                        catalog.user_roles, catalog.users))
                return catalog

            def __exit__(self, error_type, _error, _traceback):
                if error_type is None:
                    catalog.commits += 1
                else:
                    (catalog.roles, catalog.permissions,
                     catalog.user_roles, catalog.users) = self.before
                    catalog.rollbacks += 1
                return False

        return Transaction()


def memory_roles(db):
    for code in E4_ROLE_PERMISSIONS:
        db.add(Rol(codigo=code, nombre=f"Nombre personalizado {code}", permisos=[]))
    return {role.codigo: role for role in db.roles}


def assert_e4_matrix(db):
    roles = {role.codigo: role for role in db.roles}
    for code, required in E4_ROLE_PERMISSIONS.items():
        actual = {p.codigo for p in roles[code].permisos}
        assert set(required).issubset(actual)
    assert "transferencias.autorizar" not in {
        p.codigo for p in roles["ENCARGADO_INVENTARIO"].permisos
    }
    db.flush()


def unit_cli(monkeypatch, db):
    engine = Mock()
    monkeypatch.setattr("app.db.create_database_engine", lambda: engine)
    monkeypatch.setattr("app.db.create_session_factory", lambda _engine: db)
    return engine


def test_unit_empty_catalog_command_creates_base_and_exact_e4(monkeypatch, capsys):
    db = MemoryCatalog()
    engine = unit_cli(monkeypatch, db)
    before_users = deepcopy((db.user_roles, db.users))
    assert main(["--reconcile-e4"]) == 0
    assert {p.codigo for p in db.permissions} == set(PERMISSIONS)
    assert {r.codigo for r in db.roles} == set(ROLE_CATALOG)
    assert_e4_matrix(db)
    assert (db.user_roles, db.users) == before_users
    for p in db.permissions:
        assert p.descripcion == PERMISSIONS[p.codigo][0]
    output = capsys.readouterr().out
    assert "Permisos creados (14)" in output
    assert "ADMINISTRADOR (7)" in output
    assert "ENCARGADO_INVENTARIO (6)" in output
    assert "Commit confirmado" in output
    assert db.commits == 1 and db.rollbacks == 0
    engine.dispose.assert_called_once()


@pytest.mark.parametrize("state", ["before_e4", "permissions_only", "partial"])
def test_unit_existing_catalog_reconciles_only_missing_links(state):
    db = MemoryCatalog()
    roles = memory_roles(db)
    custom = Permiso(codigo="custom.read", descripcion="Personalizado")
    db.add(custom)
    for role in roles.values():
        role.permisos.append(custom)
    identities = {code: (role.id, role.nombre) for code, role in roles.items()}
    user_data = deepcopy((db.user_roles, db.users))
    if state != "before_e4":
        for code in E4_PERMISSIONS:
            db.add(Permiso(codigo=code, descripcion=PERMISSIONS[code][0]))
    if state == "partial":
        permission = next(p for p in db.permissions if p.codigo == "transferencias.consultar")
        for role in roles.values():
            role.permisos.append(permission)
    result = reconcile_e4_permissions(db)
    assert len(result["permissions_created"]) == (7 if state == "before_e4" else 0)
    assert len(result["links_added"][ADMIN_ROLE]) == (6 if state == "partial" else 7)
    assert len(result["links_added"]["ENCARGADO_INVENTARIO"]) == (5 if state == "partial" else 6)
    assert_e4_matrix(db)
    for code, role in roles.items():
        assert (role.id, role.nombre) == identities[code]
        assert custom in role.permisos
    assert (db.user_roles, db.users) == user_data
    second = reconcile_e4_permissions(db)
    assert second == {"permissions_created": [], "links_added": {
        ADMIN_ROLE: [], "ENCARGADO_INVENTARIO": [],
    }}


def test_unit_reconciliation_creates_missing_roles_without_other_permissions():
    db = MemoryCatalog()
    reconcile_e4_permissions(db)
    assert len(db.permissions) == 7
    assert {role.codigo for role in db.roles} == set(E4_ROLE_PERMISSIONS)
    assert_e4_matrix(db)


def test_unit_second_command_reports_idempotence(monkeypatch, capsys):
    db = MemoryCatalog()
    unit_cli(monkeypatch, db)
    assert main(["--reconcile-e4"]) == 0
    capsys.readouterr()
    ids = {p.codigo: p.id for p in db.permissions}
    assert main(["--reconcile-e4"]) == 0
    output = capsys.readouterr().out
    assert "Permisos creados (0)" in output
    assert "ADMINISTRADOR (0)" in output
    assert "ENCARGADO_INVENTARIO (0)" in output
    assert "Idempotencia confirmada" in output
    assert {p.codigo: p.id for p in db.permissions} == ids
    assert db.commits == 2


def test_unit_authorization_conflict_rolls_back_command(monkeypatch, capsys):
    db = MemoryCatalog()
    roles = memory_roles(db)
    forbidden = Permiso(codigo="transferencias.autorizar", descripcion="Existente")
    db.add(forbidden)
    roles["ENCARGADO_INVENTARIO"].permisos.append(forbidden)
    before_ids = {r.codigo: r.id for r in db.roles}
    before_users = deepcopy((db.user_roles, db.users))
    unit_cli(monkeypatch, db)
    assert main(["--reconcile-e4"]) == 1
    output = capsys.readouterr().err
    assert "Rollback" in output and "ENCARGADO_INVENTARIO tiene transferencias.autorizar" in output
    assert db.rollbacks == 1 and db.commits == 0
    assert {p.codigo for p in db.permissions} == {"transferencias.autorizar"}
    assert {r.codigo: r.id for r in db.roles} == before_ids
    worker = next(r for r in db.roles if r.codigo == "ENCARGADO_INVENTARIO")
    assert [p.codigo for p in worker.permisos] == ["transferencias.autorizar"]
    assert (db.user_roles, db.users) == before_users


def test_unit_sync_default_preserves_configured_roles(monkeypatch, capsys):
    db = MemoryCatalog()
    roles = memory_roles(db)
    identities = {code: (role.id, role.nombre) for code, role in roles.items()}
    unit_cli(monkeypatch, db)
    assert main([]) == 0
    assert "Seis roles configurados" in capsys.readouterr().out
    for code, role in roles.items():
        assert (role.id, role.nombre) == identities[code]
        assert role.permisos == []
    assert {p.codigo for p in db.permissions} == set(PERMISSIONS)



def test_unit_required_matrix_is_exact():
    expected = {
        "transferencias.consultar", "transferencias.solicitar",
        "transferencias.autorizar", "transferencias.despachar",
        "transferencias.recibir", "inventario.registrar_entrada", "inventario.ajustar",
    }
    assert set(E4_ROLE_PERMISSIONS[ADMIN_ROLE]) == expected
    assert len(E4_ROLE_PERMISSIONS[ADMIN_ROLE]) == 7
    assert set(E4_ROLE_PERMISSIONS["ENCARGADO_INVENTARIO"]) == (
        expected - {"transferencias.autorizar"}
    )
    assert len(E4_ROLE_PERMISSIONS["ENCARGADO_INVENTARIO"]) == 6


def test_unit_failed_verification_rolls_back_before_commit(monkeypatch, capsys):
    db = MemoryCatalog()
    unit_cli(monkeypatch, db)

    def remove_link_on_reload(role, _fields):
        if role.codigo == ADMIN_ROLE:
            role.permisos = [p for p in role.permisos if p.codigo != "transferencias.consultar"]

    monkeypatch.setattr(db, "expire", remove_link_on_reload)
    assert main(["--reconcile-e4"]) == 1
    assert "Verificación de permisos E4 fallida" in capsys.readouterr().err
    assert db.commits == 0 and db.rollbacks == 1
    assert db.roles == [] and db.permissions == []
