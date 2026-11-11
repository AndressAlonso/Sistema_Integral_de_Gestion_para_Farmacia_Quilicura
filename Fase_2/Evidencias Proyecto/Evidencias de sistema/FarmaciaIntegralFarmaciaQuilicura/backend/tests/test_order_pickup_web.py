from test_e6_cart import cart, snapshot  # noqa: F401
from test_payment_checkout import checkout  # noqa: F401
from test_payment_webhook import webhook  # noqa: F401
from test_order_pickup import ready  # noqa: F401
from app.orders.pickup import PickupService


def test_guest_pickup_requires_private_access_and_expires_after_delivery(ready):
    path = f'/api/customers/orders/{ready.order_id}/pickup-code'
    before = snapshot(ready)
    for body in ({}, {'request_token': 'x' * 64}):
        assert ready.client.post(path, json=body).status_code == 404
    body = {'request_token': ready.payment_order['request_token']}
    response = ready.client.post(path, json=body)
    assert response.status_code == 200, response.text
    assert response.headers['cache-control'] == 'no-store'
    assert response.json()['qr'] == ready.qr
    assert len(response.json()['manual_code']) == 16
    for _ in range(3):
        assert ready.client.post(path, json=body).json() == response.json()
    assert snapshot(ready) == before
    assert ready.client.post(path, json=body, headers={'Origin': 'https://attacker.example'}).status_code == 403
    PickupService(ready.factory).process(ready.pickup_actor, ready.qr, ready.order_id)
    assert ready.client.post(path, json=body).json() == {'available': False, 'status': 'RETIRADO'}


def test_unpaid_order_does_not_expose_code(checkout):
    data = checkout.payment_order
    response = checkout.client.post(f"/api/customers/orders/{data['request_id']}/pickup-code", json={'request_token': data['request_token']})
    assert response.status_code == 200
    assert response.json() == {'available': False, 'status': 'PENDIENTE_PAGO'}
