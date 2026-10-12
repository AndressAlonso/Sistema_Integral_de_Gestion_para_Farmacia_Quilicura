"""Pendiente de 0017_promociones; fixture PostgreSQL protegida con rollback."""
from decimal import Decimal
from uuid import UUID

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
