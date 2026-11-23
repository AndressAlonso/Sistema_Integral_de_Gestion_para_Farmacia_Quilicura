import io
import json
from types import SimpleNamespace
from unittest.mock import Mock
from urllib.error import HTTPError

import pytest
from pydantic import SecretStr

from app.payments.client import MercadoPagoClient, MercadoPagoError


@pytest.fixture
def client():
    settings = SimpleNamespace(access_token=SecretStr("token-ficticio"))
    instance = MercadoPagoClient(settings)
    instance.opener = Mock()
    return instance


def test_create_preference(client):
    result = {"id": "pref-123", "init_point": "https://www.mercadopago.cl/test"}
    client.opener.open.return_value = io.BytesIO(json.dumps(result).encode())
    payload = {"external_reference": "pedido-123", "items": []}

    assert client.create_preference(payload) == result
    request = client.opener.open.call_args.args[0]
    assert request.full_url == "https://api.mercadopago.com/checkout/preferences"
    assert request.get_method() == "POST"
    assert json.loads(request.data) == payload
    assert request.get_header("Authorization") == "Bearer token-ficticio"
    assert client.opener.open.call_args.kwargs["timeout"] == 15


def test_http_error_does_not_expose_body(client):
    client.opener.open.side_effect = HTTPError(
        "https://api.mercadopago.com/checkout/preferences",
        401,
        "token-ficticio",
        {},
        None,
    )
    with pytest.raises(MercadoPagoError, match="HTTP 401") as error:
        client.create_preference({})
    assert "token-ficticio" not in str(error.value)


def test_timeout_does_not_retry(client):
    client.opener.open.side_effect = TimeoutError()
    with pytest.raises(MercadoPagoError, match="No se pudo confirmar"):
        client.create_preference({})
    assert client.opener.open.call_count == 1


@pytest.mark.parametrize("body", [b"invalid", b"[]", b"{}", b'{"id": "1"}'])
def test_invalid_response(client, body):
    client.opener.open.return_value = io.BytesIO(body)
    with pytest.raises(MercadoPagoError):
        client.create_preference({})


@pytest.mark.parametrize(
    "method,path",
    [
        ("get_account", "/users/me"),
        ("get_payment", "/v1/payments/123"),
        ("get_merchant_order", "/merchant_orders/123"),
    ],
)
def test_reads_only_fixed_provider_paths(client, method, path):
    client.opener.open.return_value = io.BytesIO(b'{"id":123}')
    arguments = [] if method == "get_account" else ["123"]
    assert getattr(client, method)(*arguments) == {"id": 123}
    request = client.opener.open.call_args.args[0]
    assert request.full_url == "https://api.mercadopago.com" + path
    assert request.get_method() == "GET"
    assert client.opener.open.call_args.kwargs["timeout"] == 5


@pytest.mark.parametrize("method", ["get_payment", "get_merchant_order"])
@pytest.mark.parametrize(
    "identity", ["../users/me", "https://evil.example", "", "1?token=x"]
)
def test_invalid_identifier_never_sends_credentials(client, method, identity):
    with pytest.raises(MercadoPagoError):
        getattr(client, method)(identity)
    client.opener.open.assert_not_called()


def test_search_payments_encodes_reference_and_handles_pagination(client):
    from urllib.parse import parse_qs, urlsplit
    from uuid import uuid4

    identity = uuid4()
    first = [{"id": i, "external_reference": str(identity)} for i in range(50)]
    second = [{"id": 50, "external_reference": str(identity)}]
    client._get = Mock(
        side_effect=[
            {"paging": {"total": 51, "offset": 0}, "results": first},
            {"paging": {"total": 51, "offset": 50}, "results": second},
        ]
    )
    assert len(client.search_payments(identity)) == 51
    query = parse_qs(urlsplit(client._get.call_args.args[0]).query)
    assert query["external_reference"] == [str(identity)] and query["offset"] == ["50"]


@pytest.mark.parametrize(
    "page",
    [
        {},
        {"results": [], "paging": {"total": 1, "offset": 0}},
        {"results": [], "paging": {"total": -1, "offset": 0}},
        {"results": [], "paging": {"total": 0, "offset": 5}},
        {"results": [], "paging": {"total": "0", "offset": 0}},
    ],
)
def test_incomplete_search_is_never_treated_as_no_payment(client, page):
    from uuid import uuid4

    client._get = Mock(return_value=page)
    with pytest.raises(MercadoPagoError):
        client.search_payments(uuid4())


def test_search_rejects_payment_for_another_order(client):
    from uuid import uuid4

    client._get = Mock(
        return_value={
            "results": [{"id": 123, "external_reference": str(uuid4())}],
            "paging": {"total": 1, "offset": 0},
        }
    )
    with pytest.raises(MercadoPagoError):
        client.search_payments(uuid4())
