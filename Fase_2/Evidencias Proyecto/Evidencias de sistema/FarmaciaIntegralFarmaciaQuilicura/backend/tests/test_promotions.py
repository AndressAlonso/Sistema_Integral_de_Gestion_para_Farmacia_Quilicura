from datetime import datetime, timedelta, timezone
from decimal import Decimal
from types import SimpleNamespace
from uuid import uuid4

import pytest
from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient
from pydantic import ValidationError

from app.pos.pricing import Promotion, best_price
from app.promotions import routes
from app.promotions.schemas import PromotionInput

NOW = datetime(2026, 10, 12, 12, tzinfo=timezone.utc)
PRODUCT = uuid4()
CATEGORY = uuid4()


def payload(**changes):
    return {"name": " Oferta ", "kind": "PERCENT", "value": "20.00",
        "starts_at": NOW.isoformat(), "ends_at": (NOW + timedelta(days=1)).isoformat(),
        "product_id": str(PRODUCT), **changes}


@pytest.mark.parametrize("changes", [
    {"name": "   "}, {"kind": "OTHER"}, {"value": "-1"}, {"value": "101"},
    {"value": "1.001"}, {"ends_at": NOW.isoformat()},
    {"starts_at": "2026-10-12T12:00:00"}, {"product_id": None},
    {"category_id": str(CATEGORY)}, {"unexpected": True},
])
def test_invalid_input(changes):
    with pytest.raises(ValidationError):
        PromotionInput.model_validate(payload(**changes))


def test_valid_product_category_and_fixed_price():
    assert PromotionInput.model_validate(payload()).name == "Oferta"
    assert PromotionInput.model_validate(payload(product_id=None, category_id=str(CATEGORY))).category_id == CATEGORY
    assert PromotionInput.model_validate(payload(kind="FIXED_PRICE", value="700")).value == Decimal(700)


def test_lowest_price_validity_and_no_stacking():
    promos = (
        Promotion("p", "Porcentaje", "PERCENT", Decimal(20), NOW, NOW + timedelta(days=1), PRODUCT),
        Promotion("c", "Categoría", "FIXED_PRICE", Decimal(700), NOW, NOW + timedelta(days=1), category_id=CATEGORY),
        Promotion("future", "Futura", "PERCENT", Decimal(99), NOW + timedelta(days=1), NOW + timedelta(days=2), PRODUCT),
    )
    price, chosen = best_price(Decimal(1000), PRODUCT, CATEGORY, NOW, promos)
    assert price == Decimal(700) and chosen["code"] == "c"
    assert best_price(Decimal(1000), PRODUCT, CATEGORY, NOW + timedelta(days=1), promos)[0] == Decimal(10)
    assert best_price(Decimal(1000), PRODUCT, CATEGORY, NOW - timedelta(seconds=1), promos) == (Decimal(1000), None)
    assert best_price(Decimal(500), PRODUCT, CATEGORY, NOW, promos)[0] == Decimal(400)


@pytest.mark.parametrize("roles,permissions,allowed", [
    (["ADMINISTRADOR"], ["catalogo.gestionar"], True),
    (["ADMINISTRADOR"], [], False),
    (["ENCARGADO_INVENTARIO"], ["catalogo.gestionar"], False),
])
def test_permissions(monkeypatch, roles, permissions, allowed):
    actor = SimpleNamespace(roles=roles, permissions=permissions)
    monkeypatch.setattr(routes, "authenticated_user", lambda request: (actor, None))
    if allowed:
        assert routes.manager(None) is actor
    else:
        with pytest.raises(HTTPException) as exc:
            routes.manager(None)
        assert exc.value.status_code == 403


def test_endpoint_contract_and_extra_fields(monkeypatch):
    app = FastAPI()
    app.include_router(routes.router)
    actor = SimpleNamespace(id=uuid4())
    app.dependency_overrides[routes.manager] = lambda: actor
    calls = []
    def save(data, user, promotion_id=None):
        calls.append((data, user, promotion_id))
        return {**data.model_dump(), "id": promotion_id or uuid4(), "created_at": NOW}
    app.state.promotions = SimpleNamespace(save=save, list=list)
    monkeypatch.setattr(routes, "check_origin", lambda request: None)
    with TestClient(app) as client:
        assert client.get("/api/promotions").json() == []
        response = client.post("/api/promotions", json=payload())
        assert response.status_code == 201
        assert response.json()["value"] == "20.00"
        key = response.json()["id"]
        assert client.patch(f"/api/promotions/{key}", json=payload(is_active=False)).status_code == 200
        assert client.post("/api/promotions", json=payload(secret="x")).status_code == 422
        assert len(calls) == 2 and calls[-1][0].is_active is False
