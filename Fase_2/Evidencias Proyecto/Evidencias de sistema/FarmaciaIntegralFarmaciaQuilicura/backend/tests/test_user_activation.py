from uuid import uuid4

from test_auth import login

from app.auth.routes import COOKIE_NAME


def test_activation_restores_login_but_not_revoked_sessions(setup):
    login(setup, 'operator')
    old_token = setup.client.cookies.get(COOKIE_NAME)
    login(setup)
    target = setup.ids['operator']
    assert setup.client.post(f'/api/users/{target}/deactivate').status_code == 200
    response = setup.client.post(f'/api/users/{target}/activate')
    assert response.status_code == 200
    assert response.json()['is_active'] is True
    assert setup.client.post(f'/api/users/{target}/activate').status_code == 200
    setup.client.cookies.clear()
    setup.client.cookies.set(COOKIE_NAME, old_token)
    assert setup.client.get('/api/auth/me').status_code == 401
    assert login(setup, 'operator').status_code == 200


def test_activation_requires_permission_and_trusted_origin(setup):
    url = f"/api/users/{setup.ids['inactive']}/activate"
    assert setup.client.post(url).status_code == 401
    login(setup, 'operator')
    assert setup.client.post(url).status_code == 403
    login(setup)
    assert setup.client.post(url, headers={'Origin': 'https://untrusted.example'}).status_code == 403
    assert setup.client.post(f'/api/users/{uuid4()}/activate').status_code == 404
