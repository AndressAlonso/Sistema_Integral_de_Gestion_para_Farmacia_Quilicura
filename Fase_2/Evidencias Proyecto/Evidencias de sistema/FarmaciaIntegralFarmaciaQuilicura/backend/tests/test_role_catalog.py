import pytest
from sqlalchemy import select
from test_auth import login
from test_users import payload

from app.models import Rol, UsuarioInterno
from app.role_catalog import ADMIN_ROLE, ROLE_CATALOG, sync_roles


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
