"""Pendiente de 0017_promociones; fixture PostgreSQL protegida con rollback."""
from decimal import Decimal
from uuid import UUID

import pytest
from app.models import EventoAuditoria, InventarioSucursal, Permiso, Promocion, Rol
from sqlalchemy import select
from test_auth import login
from test_pos import pos  # noqa: F401
from test_promotions import payload
from test_transfers import transfer  # noqa: F401


def test_persistence_audit_and_pos_pricing(pos):  # noqa: F811
    with pos.factory.begin() as db:
        role = db.get(Rol, pos.ids["admin_role"])
        permission = db.scalar(select(Permiso).where(Permiso.codigo == "catalogo.gestionar"))
        if permission is None:
            permission = Permiso(codigo="catalogo.gestionar", descripcion="Fixture temporal E2-H3")
            db.add(permission)
        if permission not in role.permisos:
            role.permisos.append(permission)
    assert login(pos, "admin").status_code == 200
    data = payload(product_id=str(pos.product_id), starts_at="2020-01-01T00:00:00Z", ends_at="2090-01-01T00:00:00Z")
    with pos.factory() as db:
        before = db.get(InventarioSucursal, pos.inventory_id).stock_fisico
    response = pos.client.post("/api/promotions", json=data)
    assert response.status_code == 201, response.text
    row = response.json()
    quote = pos.client.post("/api/pos/quote", json={"items": [{"product_id": str(pos.product_id), "quantity": 1}]}).json()
    line = quote["items"][0]
    assert Decimal(line["price"]) == Decimal(line["base_price"]) * Decimal("0.8")
    assert line["promotion"]["code"] == row["id"]
    assert pos.client.patch(f"/api/promotions/{row['id']}", json={**data, "is_active": False}).status_code == 200
    with pos.factory() as db:
        assert db.get(Promocion, UUID(row["id"])).activo is False
        assert db.scalar(select(EventoAuditoria).where(EventoAuditoria.referencia_historica == row["id"])) is not None
        assert db.get(InventarioSucursal, pos.inventory_id).stock_fisico == before


@pytest.mark.parametrize("kind,value,expected", [("PERCENT", "20", "800.00"), ("FIXED_PRICE", "650", "650.00")])
def test_pos_search_and_checkout_show_same_active_promotion(pos, kind, value, expected):  # noqa: F811
    with pos.factory.begin() as db:
        role = db.get(Rol, pos.ids["admin_role"])
        permission = db.scalar(select(Permiso).where(Permiso.codigo == "catalogo.gestionar"))
        if permission is None:
            permission = Permiso(codigo="catalogo.gestionar", descripcion="Fixture promoción")
            db.add(permission)
        if permission not in role.permisos: role.permisos.append(permission)
    assert login(pos, "admin").status_code == 200
    data = payload(product_id=str(pos.product_id), kind=kind, value=value,
        starts_at="2020-01-01T00:00:00Z", ends_at="2090-01-01T00:00:00Z")
    response = pos.client.post("/api/promotions", json=data)
    assert response.status_code == 201, response.text
    identity = response.json()["id"]
    def search():
        return next(row for row in pos.client.get("/api/pos/products", params={"q":str(pos.product_id)}).json()["products"] if row["id"] == str(pos.product_id))
    product = search()
    quote = pos.client.post("/api/pos/quote", json={"items":[{"product_id":str(pos.product_id),"quantity":2}]}).json()
    line = quote["items"][0]
    assert product["price"] == line["price"] == expected
    assert Decimal(product["base_price"]) == Decimal(line["base_price"]) == Decimal(1000)
    assert product["promotion"] == line["promotion"]
    assert product["promotion"]["kind"] == kind
    assert Decimal(quote["discount"]) == (Decimal(1000)-Decimal(expected))*2
    assert pos.client.patch(f"/api/promotions/{identity}", json={**data,"is_active":False}).status_code == 200
    product = search()
    assert product["promotion"] is None and Decimal(product["price"]) == Decimal(1000)
