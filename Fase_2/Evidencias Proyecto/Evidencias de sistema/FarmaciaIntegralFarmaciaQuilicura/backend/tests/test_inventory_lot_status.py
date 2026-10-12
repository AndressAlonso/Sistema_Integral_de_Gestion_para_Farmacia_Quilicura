"""Reactivación desde Inventario con PostgreSQL y rollback, independiente de recepción."""
from uuid import UUID

import pytest
from app.models import (
    EventoAuditoria,
    LoteInventario,
    MovimientoInventario,
    Permiso,
    Rol,
    Transferencia,
)
from sqlalchemy import func, select
from test_auth import login
from test_receipt_review import blocked  # noqa: F401
from test_transfers import destination_inventory, transfer  # noqa: F401


@pytest.fixture
def inventory_lot(blocked):  # noqa: F811 -- fixture protegida de PostgreSQL
    with blocked.factory.begin() as db:
        permission = db.scalar(select(Permiso).where(Permiso.codigo == "inventario.consultar"))
        if permission is None:
            permission = Permiso(codigo="inventario.consultar", descripcion="Fixture temporal")
            db.add(permission)
        role = db.get(Rol, blocked.ids["operator_role"])
        if permission not in role.permisos:
            role.permisos.append(permission)
    assert login(blocked, "operator").status_code == 200
    return blocked


def reactivate(ctx, **changes):
    data = {"reason": "Revisión del lote desde Inventario", "confirmed": True,
            "expected_expiration_date": ctx.blocked_expiration.isoformat(), "expected_quantity": 0}
    return ctx.client.post(f"/api/inventory/lots/{ctx.blocked_lot}/reactivate", json=data | changes)


def test_inventory_reactivation_keeps_quantities_and_date_and_is_audited(inventory_lot):
    ctx = inventory_lot
    response = ctx.client.get(f"/api/inventory/lots/{ctx.blocked_lot}/status")
    assert response.status_code == 200, response.text
    assert response.json()["can_reactivate"] and response.json()["quantity"] == 0
    with ctx.factory() as db:
        movements = db.scalar(select(func.count()).select_from(MovimientoInventario))
    response = reactivate(ctx)
    assert response.status_code == 200 and response.json()["changed"]
    assert reactivate(ctx).json()["changed"] is False
    with ctx.factory() as db:
        lot = db.get(LoteInventario, ctx.blocked_lot)
        assert lot.activo and lot.cantidad == 0 and lot.fecha_vencimiento == ctx.blocked_expiration
        assert destination_inventory(db, ctx).stock_fisico == 0
        assert db.get(Transferencia, UUID(ctx.payload["request_id"])).estado == "EN_TRANSITO"
        assert db.scalar(select(func.count()).select_from(MovimientoInventario)) == movements
        events = list(db.scalars(select(EventoAuditoria).where(EventoAuditoria.referencia_historica == str(lot.id), EventoAuditoria.accion == "LOTE_REACTIVADO")))
        assert len(events) == 1 and events[0].usuario_id == ctx.ids["operator"]
        assert events[0].datos_cambio["motivo"] == "Revisión del lote desde Inventario"


def test_inventory_reactivation_requires_reason_confirmation_and_current_snapshot(inventory_lot):
    assert reactivate(inventory_lot, reason=" ").status_code == 422
    assert reactivate(inventory_lot, confirmed=False).status_code == 422
    assert reactivate(inventory_lot, expected_quantity=10).status_code == 409
    with inventory_lot.factory() as db:
        assert db.get(LoteInventario, inventory_lot.blocked_lot).activo is False


def test_inventory_reactivation_rejects_missing_permission(inventory_lot):
    ctx = inventory_lot
    with ctx.factory.begin() as db:
        role = db.get(Rol, ctx.ids["operator_role"])
        role.permisos = [permission for permission in role.permisos if permission.codigo != "inventario.gestionar_lotes"]
    assert login(ctx, "operator").status_code == 200
    assert ctx.client.get(f"/api/inventory/lots/{ctx.blocked_lot}/status").json()["can_reactivate"] is False
    assert reactivate(ctx).status_code == 403


def test_inventory_reactivation_rejects_invalid_origin(inventory_lot):
    ctx = inventory_lot
    result = ctx.client.post(f"/api/inventory/lots/{ctx.blocked_lot}/reactivate",
        json={"reason": "Revisión autorizada", "confirmed": True, "expected_quantity": 0,
              "expected_expiration_date": ctx.blocked_expiration.isoformat()},
        headers={"Origin": "https://otro-origen.invalid"})
    assert result.status_code == 403
    with ctx.factory() as db:
        assert db.get(LoteInventario, ctx.blocked_lot).activo is False


@pytest.fixture
def enabled_lot(inventory_lot):
    ctx = inventory_lot
    assert reactivate(ctx).status_code == 200
    with ctx.factory.begin() as db:
        db.get(LoteInventario, ctx.blocked_lot).cantidad = 28
        destination_inventory(db, ctx).stock_fisico = 28
    return ctx


def disable(ctx, **changes):
    data = {"reason": "Envases dañados", "confirmed": True,
            "expected_expiration_date": ctx.blocked_expiration.isoformat(), "expected_quantity": 28}
    return ctx.client.post(f"/api/inventory/lots/{ctx.blocked_lot}/disable", json=data | changes)


def test_disable_is_audited_idempotent_and_preserves_inventory(enabled_lot):
    ctx = enabled_lot
    assert ctx.client.get(f"/api/inventory/lots/{ctx.blocked_lot}/status").json()["can_disable"]
    with ctx.factory() as db:
        movements = db.scalar(select(func.count()).select_from(MovimientoInventario))
        reserved = destination_inventory(db, ctx).stock_reservado
    assert disable(ctx).json()["changed"] is True
    assert disable(ctx).json()["changed"] is False
    status = ctx.client.get(f"/api/inventory/lots/{ctx.blocked_lot}/status").json()
    assert not status["is_active"] and not status["can_disable"] and status["can_reactivate"]
    with ctx.factory() as db:
        lot = db.get(LoteInventario, ctx.blocked_lot)
        assert not lot.activo and lot.cantidad == 28 and lot.fecha_vencimiento == ctx.blocked_expiration
        inventory = destination_inventory(db, ctx)
        assert inventory.stock_fisico == 28 and inventory.stock_reservado == reserved
        assert db.scalar(select(func.count()).select_from(MovimientoInventario)) == movements
        events = list(db.scalars(select(EventoAuditoria).where(
            EventoAuditoria.referencia_historica == str(lot.id), EventoAuditoria.accion == "LOTE_DESHABILITADO")))
        assert len(events) == 1 and events[0].usuario_id == ctx.ids["operator"]
        assert events[0].datos_cambio["motivo"] == "Envases dañados"


@pytest.mark.parametrize("changes,code", [({"reason": "  "}, 422), ({"confirmed": False}, 422),
    ({"expected_quantity": 29}, 409), ({"expected_expiration_date": "2000-01-01"}, 409)])
def test_disable_requires_reason_confirmation_and_fresh_snapshot(enabled_lot, changes, code):
    assert disable(enabled_lot, **changes).status_code == code
    with enabled_lot.factory() as db:
        assert db.get(LoteInventario, enabled_lot.blocked_lot).activo


def test_disable_rejects_missing_permission(enabled_lot):
    ctx = enabled_lot
    with ctx.factory.begin() as db:
        role = db.get(Rol, ctx.ids["operator_role"])
        role.permisos = [permission for permission in role.permisos if permission.codigo != "inventario.gestionar_lotes"]
    assert login(ctx, "operator").status_code == 200
    assert not ctx.client.get(f"/api/inventory/lots/{ctx.blocked_lot}/status").json()["can_disable"]
    assert disable(ctx).status_code == 403
    with ctx.factory() as db:
        assert db.get(LoteInventario, ctx.blocked_lot).activo


def test_disable_rejects_foreign_origin(enabled_lot):
    ctx = enabled_lot
    result = ctx.client.post(f"/api/inventory/lots/{ctx.blocked_lot}/disable",
        json={"reason": "Envases dañados", "confirmed": True, "expected_quantity": 28,
              "expected_expiration_date": ctx.blocked_expiration.isoformat()},
        headers={"Origin": "https://otro-origen.invalid"})
    assert result.status_code == 403
    with ctx.factory() as db:
        assert db.get(LoteInventario, ctx.blocked_lot).activo
