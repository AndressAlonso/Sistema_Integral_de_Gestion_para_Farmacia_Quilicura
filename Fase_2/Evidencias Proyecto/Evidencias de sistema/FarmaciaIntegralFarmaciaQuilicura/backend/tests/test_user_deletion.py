from uuid import UUID, uuid4

import pytest
from sqlalchemy import select
from test_auth import login
from test_users import payload

from app.auth.routes import COOKIE_NAME
from app.models import Rol, SesionInterna, UsuarioInterno


def test_delete_unused_user_and_remove_role_assignment(setup):
    login(setup)
    user = setup.client.post('/api/users', json=payload(setup)).json()
    listed = setup.client.get('/api/users').json()['users']
    assert next(row for row in listed if row['id'] == user['id'])['can_delete']
    response = setup.client.post(f"/api/users/{user['id']}/delete", json={
        'confirmation_email': user['email'],
    })
    assert response.status_code == 204
    with setup.factory() as db:
        assert db.get(UsuarioInterno, UUID(user['id'])) is None


@pytest.mark.parametrize('body', [{}, {'confirmation_email': 'invalid'},
                                 {'confirmation_email': 'different@farmacia.cl'}])
def test_delete_bad_confirmation_preserves_user(setup, body):
    login(setup)
    user = setup.client.post('/api/users', json=payload(setup)).json()
    assert setup.client.post(f"/api/users/{user['id']}/delete", json=body).status_code == 422
    with setup.factory() as db:
        assert db.get(UsuarioInterno, UUID(user['id'])) is not None


def test_cannot_delete_self(setup):
    login(setup)
    response = setup.client.post(f"/api/users/{setup.ids['admin']}/delete", json={
        'confirmation_email': setup.emails['admin'],
    })
    assert response.status_code == 409


@pytest.mark.parametrize('logged_out', [False, True])
def test_delete_user_with_sessions_invalidates_token(setup, logged_out):
    login(setup, 'operator')
    token = setup.client.cookies.get(COOKIE_NAME)
    if logged_out:
        setup.client.post('/api/auth/logout')
    login(setup)
    listed = setup.client.get('/api/users').json()['users']
    assert next(row for row in listed if row['id'] == str(setup.ids['operator']))['can_delete']
    response = setup.client.post(f"/api/users/{setup.ids['operator']}/delete", json={
        'confirmation_email': setup.emails['operator'],
    })
    assert response.status_code == 204
    with setup.factory() as db:
        assert db.get(UsuarioInterno, setup.ids['operator']) is None
        assert not db.scalars(select(SesionInterna).where(
            SesionInterna.usuario_id == setup.ids['operator'],
        )).all()
        assert db.scalars(select(SesionInterna).where(
            SesionInterna.usuario_id == setup.ids['admin'],
        )).all()
    setup.client.cookies.clear()
    setup.client.cookies.set(COOKIE_NAME, token)
    assert setup.client.get('/api/auth/me').status_code == 401
    assert login(setup, 'operator').status_code == 401


def test_last_active_admin_cannot_be_deleted(setup):
    login(setup)
    with setup.factory.begin() as db:
        admin_role = db.scalar(select(Rol).where(Rol.codigo == 'ADMINISTRADOR'))
        if admin_role is None:
            admin_role = Rol(codigo='ADMINISTRADOR', nombre='Administrador')
            db.add(admin_role)
        for user in db.scalars(select(UsuarioInterno).where(
            UsuarioInterno.roles.any(Rol.codigo == 'ADMINISTRADOR'),
        )):
            user.activo = False
        target = db.get(UsuarioInterno, setup.ids['operator'])
        target.roles = [admin_role]
        target.activo = True
    response = setup.client.post(f"/api/users/{setup.ids['operator']}/delete", json={
        'confirmation_email': setup.emails['operator'],
    })
    assert response.status_code == 409
    assert 'último administrador' in response.json()['detail']


def test_delete_requires_auth_permission_and_trusted_origin(setup):
    url = f"/api/users/{setup.ids['inactive']}/delete"
    body = {'confirmation_email': setup.emails['inactive']}
    assert setup.client.post(url, json=body).status_code == 401
    login(setup, 'operator')
    assert setup.client.post(url, json=body).status_code == 403
    login(setup)
    assert setup.client.post(url, json=body, headers={
        'Origin': 'https://untrusted.example',
    }).status_code == 403
    assert setup.client.post(f'/api/users/{uuid4()}/delete', json=body).status_code == 404
