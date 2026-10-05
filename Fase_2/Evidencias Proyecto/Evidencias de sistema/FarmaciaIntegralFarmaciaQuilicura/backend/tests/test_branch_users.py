from uuid import uuid4

from sqlalchemy import select
from test_auth import login
from test_branches import branch_payload

from app.models import Permiso, Rol, UsuarioInterno


def test_assigned_users_are_scoped_and_expose_only_public_fields(setup):
    login(setup)
    empty = setup.client.post('/api/branches', json=branch_payload(setup)).json()
    assert setup.client.get(f"/api/branches/{empty['id']}/users").json() == {'users': []}
    response = setup.client.get(f"/api/branches/{setup.ids['branch']}/users")
    assert response.status_code == 200
    users = response.json()['users']
    assert {user['id'] for user in users} == {
        str(setup.ids[name]) for name in ('admin', 'operator', 'inactive', 'manager')
    }
    assert any(not user['is_active'] for user in users)
    assert all(set(user) == {'id', 'name', 'email', 'roles', 'is_active'} for user in users)
    assert all(user['roles'] for user in users)
    listed = setup.client.get('/api/branches').json()['branches']
    current = next(row for row in listed if row['id'] == str(setup.ids['branch']))
    assert current['assigned_users_count'] == len(users) == 4
    assert next(row for row in listed if row['id'] == empty['id'])['assigned_users_count'] == 0
    updated = setup.client.patch(f"/api/branches/{setup.ids['branch']}", json={'name': 'Nombre actualizado'})
    assert updated.json()['assigned_users_count'] == 4


def test_branch_user_list_requires_branch_permission_not_user_management(setup):
    url = f"/api/branches/{setup.ids['branch']}/users"
    assert setup.client.get(url).status_code == 401
    login(setup, 'manager')
    assert setup.client.get(url).status_code == 403
    with setup.factory.begin() as db:
        permission = db.scalar(select(Permiso).where(Permiso.codigo == 'sucursales.gestionar'))
        role = Rol(codigo=f'BRANCH_ONLY_{setup.suffix}', nombre='Gestor de sucursal', permisos=[permission])
        db.get(UsuarioInterno, setup.ids['operator']).roles = [role]
    login(setup, 'operator')
    assert setup.client.get(url).status_code == 200
    assert setup.client.get('/api/users').status_code == 403
    assert setup.client.get(f'/api/branches/{uuid4()}/users').status_code == 404
