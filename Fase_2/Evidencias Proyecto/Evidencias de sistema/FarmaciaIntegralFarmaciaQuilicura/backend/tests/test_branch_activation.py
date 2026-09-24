from uuid import uuid4

from test_auth import login
from test_branches import branch_payload


def test_activate_branch_preserves_data_and_is_repeatable(setup):
    login(setup)
    created = setup.client.post('/api/branches', json=branch_payload(setup, is_active=False)).json()
    url = f"/api/branches/{created['id']}/activate"
    for _ in range(2):
        response = setup.client.post(url)
        assert response.status_code == 200
        assert response.json() == {**created, 'is_active': True}
    listed = setup.client.get('/api/branches').json()['branches']
    assert next(row for row in listed if row['id'] == created['id'])['is_active']
    assert setup.client.post(f"/api/branches/{created['id']}/deactivate").status_code == 200


def test_activate_branch_requires_permission_and_trusted_origin(setup):
    url = f"/api/branches/{setup.ids['branch']}/activate"
    assert setup.client.post(url).status_code == 401
    login(setup, 'operator')
    assert setup.client.post(url).status_code == 403
    login(setup)
    assert setup.client.post(url, headers={'Origin': 'https://untrusted.example'}).status_code == 403
    assert setup.client.post(f'/api/branches/{uuid4()}/activate').status_code == 404
