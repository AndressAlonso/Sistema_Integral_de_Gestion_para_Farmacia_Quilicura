from uuid import uuid4

import pytest
from sqlalchemy import select
from test_auth import login
from test_users import payload

from app.models import Rol, UsuarioInterno
from app.role_catalog import sync_roles

URL = '/api/users/roles'


def catalog(setup):
    response = setup.client.get(URL)
    assert response.status_code == 200
    return response.json()


def role_input(setup, **changes):
    return {'code': f'SUPERVISOR_{setup.suffix}', 'name': 'Supervisor',
            'permission_ids': [], **changes}


def patch_input(role, **changes):
    return {'name': role['name'], 'permission_ids': role['permission_ids'],
            'revision': role['revision'], **changes}


def test_create_assign_and_update_role_changes_existing_session_permissions(setup):
    login(setup)
    permissions = {row['code']: row['id'] for row in catalog(setup)['permissions']}
    created = setup.client.post(URL, json=role_input(setup, permission_ids=[permissions['usuarios.gestionar']]))
    assert created.status_code == 201
    role = created.json()
    assert role['users_count'] == 0
    assert role['code'] == role_input(setup)['code'].upper()
    assert setup.client.patch(f"/api/users/{setup.ids['operator']}", json={'role_ids': [role['id']]}).status_code == 200
    login(setup, 'operator')
    from app.auth.routes import COOKIE_NAME
    token = setup.client.cookies.get(COOKIE_NAME)
    assert setup.client.get('/api/users').status_code == 200
    login(setup)
    role = next(row for row in catalog(setup)['roles'] if row['id'] == role['id'])
    assert role['users_count'] == 1
    result = setup.client.patch(f"{URL}/{role['id']}", json=patch_input(role, name='Supervisor actualizado', permission_ids=[]))
    assert result.status_code == 200
    assert result.json()['code'] == role['code']
    setup.client.cookies.clear()
    setup.client.cookies.set(COOKIE_NAME, token)
    assert setup.client.get('/api/auth/me').json()['user']['permissions'] == []
    assert setup.client.get('/api/users').status_code == 403


@pytest.mark.parametrize('name', [None, 'operator', 'manager'])
def test_role_operations_require_both_permissions(setup, name):
    if name:
        login(setup, name)
    expected = 403 if name else 401
    assert setup.client.get(URL).status_code == expected
    assert setup.client.post(URL, json=role_input(setup)).status_code == expected
    assert setup.client.patch(f"{URL}/{setup.ids['admin_role']}", json={
        'name': 'Alterado', 'permission_ids': [], 'revision': '0' * 64,
    }).status_code == expected


@pytest.mark.parametrize('changes', [
    {'name': ' '}, {'name': 'x' * 101}, {'code': 'A-B'}, {'code': ''},
    {'permission_ids': [str(uuid4())]}, {'permission_ids': None},
    {'description': 'No hay columna de descripción'},
])
def test_invalid_role_input_is_rejected_without_partial_creation(setup, changes):
    login(setup)
    before = len(catalog(setup)['roles'])
    assert setup.client.post(URL, json=role_input(setup, **changes)).status_code == 422
    assert len(catalog(setup)['roles']) == before


def test_duplicate_code_and_duplicate_permissions(setup):
    login(setup)
    permission_id = catalog(setup)['permissions'][0]['id']
    assert setup.client.post(URL, json=role_input(setup)).status_code == 201
    assert setup.client.post(URL, json=role_input(setup)).status_code == 409
    assert setup.client.post(URL, json=role_input(setup, permission_ids=[permission_id, permission_id])).status_code == 422


def test_role_conflicts_and_immutable_code(setup):
    login(setup)
    role = setup.client.post(URL, json=role_input(setup)).json()
    data = patch_input(role, name='Nombre cambiado')
    assert setup.client.patch(f"{URL}/{role['id']}", json=data).status_code == 200
    assert setup.client.patch(f"{URL}/{role['id']}", json=data).status_code == 409
    assert setup.client.patch(f"{URL}/{role['id']}", json={**data, 'code': 'OTRO'}).status_code == 422
    assert setup.client.patch(f'{URL}/{uuid4()}', json=data).status_code == 404
    assert setup.client.post(URL, json=role_input(setup, code='OPERADOR')).status_code == 409


def test_assignment_change_requires_refresh_before_role_update(setup):
    login(setup)
    role = setup.client.post(URL, json=role_input(setup)).json()
    assert setup.client.post('/api/users', json=payload(setup, role_ids=[role['id']])).status_code == 201
    assert setup.client.patch(f"{URL}/{role['id']}", json=patch_input(role)).status_code == 409


def test_cannot_remove_last_active_access_manager_permissions(setup):
    login(setup)
    with setup.factory.begin() as db:
        for user in db.scalars(select(UsuarioInterno).where(UsuarioInterno.id != setup.ids['admin'])):
            user.activo = False
    role = next(row for row in catalog(setup)['roles'] if row['id'] == str(setup.ids['admin_role']))
    response = setup.client.patch(f"{URL}/{role['id']}", json=patch_input(role, name='No debe persistir', permission_ids=[]))
    assert response.status_code == 409
    assert 'cuenta activa' in response.json()['detail']
    current = next(row for row in catalog(setup)['roles'] if row['id'] == role['id'])
    assert current == role


def test_sync_preserves_configured_role_names_and_permissions(setup):
    with setup.factory.begin() as db:
        roles = sync_roles(db)
        role = roles['ENCARGADO_INVENTARIO']
        role.nombre = 'Inventario personalizado'
        role.permisos = []
        db.flush()
        role_id = role.id
        sync_roles(db)
        assert db.get(Rol, role_id).nombre == 'Inventario personalizado'
        assert db.get(Rol, role_id).permisos == []


def test_role_mutations_require_trusted_origin(setup):
    login(setup)
    role = setup.client.post(URL, json=role_input(setup)).json()
    headers = {'Origin': 'https://untrusted.example'}
    assert setup.client.post(URL, json=role_input(setup), headers=headers).status_code == 403
    assert setup.client.patch(f"{URL}/{role['id']}", json=patch_input(role), headers=headers).status_code == 403
