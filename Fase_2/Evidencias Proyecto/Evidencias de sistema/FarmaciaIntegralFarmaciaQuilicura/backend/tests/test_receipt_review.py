"""Reactivación autorizada con rollback; nunca incorpora stock automáticamente."""
from datetime import datetime, timedelta, timezone
from uuid import UUID

import pytest
from sqlalchemy import func, select
from test_auth import login
from test_transfers import (  # noqa: F401
    change,
    destination_inventory,
    transfer,
    transit,
)

from app.models import (
    EventoAuditoria,
    InventarioSucursal,
    LoteInventario,
    MovimientoInventario,
    Permiso,
    Rol,
    Transferencia,
)


@pytest.fixture
def blocked(transfer):  # noqa: F811 -- fixture importada de PostgreSQL con rollback
    transit(transfer)
    with transfer.factory.begin() as db:
        source = db.get(LoteInventario, transfer.late_id)
        inv = InventarioSucursal(producto_id=transfer.product_id, sucursal_id=transfer.destination_id,
                                 stock_fisico=0, stock_reservado=0)
        db.add(inv)
        db.flush()
        lot = LoteInventario(inventario_sucursal_id=inv.id, numero_lote=source.numero_lote,
                            fecha_vencimiento=source.fecha_vencimiento, cantidad=0, activo=False)
        db.add(lot)
        db.flush()
        transfer.blocked_lot = lot.id
        transfer.blocked_expiration = lot.fecha_vencimiento
        permission = db.scalar(select(Permiso).where(Permiso.codigo == "inventario.gestionar_lotes"))
        if permission is None:
            permission = Permiso(codigo="inventario.gestionar_lotes", descripcion="Fixture temporal")
            db.add(permission)
        role = db.get(Rol, transfer.ids["operator_role"])
        role.permisos.append(permission)
    assert login(transfer, "operator").status_code == 200
    return transfer


def review(ctx):
    return ctx.client.get(f"/api/transfers/{ctx.payload['request_id']}/receipt-review")


def reactivate(ctx, **changes):
    data = {"reason": "Revisión autorizada de datos de prueba", "confirmed": True,
            "expected_expiration_date": ctx.blocked_expiration.isoformat(), "expected_quantity": 0}
    return ctx.client.post(f"/api/transfers/{ctx.payload['request_id']}/destination-lots/{ctx.blocked_lot}/reactivate",
                           json=data | changes)


def assert_unchanged(ctx):
    with ctx.factory() as db:
        lot = db.get(LoteInventario, ctx.blocked_lot)
        assert lot.activo is False and lot.cantidad == 0 and lot.fecha_vencimiento == ctx.blocked_expiration
        assert destination_inventory(db, ctx).stock_fisico == 0
        assert db.get(Transferencia, UUID(ctx.payload["request_id"])).estado == "EN_TRANSITO"


def test_review_does_not_modify_lots_and_identifies_reactivation(blocked):
    response = review(blocked)
    assert response.status_code == 200, response.text
    lot = next(item for item in response.json()["items"] if item["number"] == "SEGUNDO")
    assert lot["conflicts"] == ["INACTIVE"] and lot["can_reactivate"] is True
    assert lot["destination_quantity"] == 0 and lot["source_expiration"] == lot["destination_expiration"]
    assert_unchanged(blocked)


def test_reactivate_is_audited_idempotent_and_receipt_remains_separate(blocked):
    with blocked.factory() as db:
        movements = db.scalar(select(func.count()).select_from(MovimientoInventario))
    result = reactivate(blocked)
    assert result.status_code == 200 and result.json()["changed"] is True
    assert reactivate(blocked).json()["changed"] is False
    with blocked.factory() as db:
        lot = db.get(LoteInventario, blocked.blocked_lot)
        assert lot.activo and lot.cantidad == 0 and lot.fecha_vencimiento == blocked.blocked_expiration
        assert destination_inventory(db, blocked).stock_fisico == 0
        assert db.get(Transferencia, UUID(blocked.payload["request_id"])).estado == "EN_TRANSITO"
        assert db.scalar(select(func.count()).select_from(MovimientoInventario)) == movements
        events = list(db.scalars(select(EventoAuditoria).where(EventoAuditoria.referencia_historica == str(lot.id),
                                                            EventoAuditoria.accion == "LOTE_REACTIVADO")))
        assert len(events) == 1 and events[0].usuario_id == blocked.ids["operator"]
        assert events[0].datos_cambio["motivo"] == "Revisión autorizada de datos de prueba"
    assert change(blocked, "receive", {"items": blocked.payload["items"]}).status_code == 200
    with blocked.factory() as db:
        assert destination_inventory(db, blocked).stock_fisico == 8
        assert db.get(Transferencia, UUID(blocked.payload["request_id"])).estado == "RECIBIDA"


@pytest.mark.parametrize("changes", [{"reason": " "}, {"confirmed": False}, {"unexpected": "x"}])
def test_reason_confirmation_and_strict_contract(blocked, changes):
    assert reactivate(blocked, **changes).status_code == 422
    assert_unchanged(blocked)


def test_stale_quantity_is_rejected(blocked):
    assert reactivate(blocked, expected_quantity=1).status_code == 409
    assert_unchanged(blocked)


def test_mismatched_dates_are_not_repaired_automatically(blocked):
    with blocked.factory.begin() as db:
        lot = db.get(LoteInventario, blocked.blocked_lot)
        lot.fecha_vencimiento += timedelta(days=1)
        blocked.blocked_expiration = lot.fecha_vencimiento
    item = next(item for item in review(blocked).json()["items"] if item["number"] == "SEGUNDO")
    assert item["can_reactivate"] is False and "EXPIRATION_MISMATCH" in item["conflicts"]
    assert reactivate(blocked).status_code == 409
    assert_unchanged(blocked)


def test_missing_inventory_permission_is_enforced_in_backend(blocked):
    with blocked.factory.begin() as db:
        role = db.get(Rol, blocked.ids["operator_role"])
        role.permisos = [permission for permission in role.permisos if permission.codigo != "inventario.gestionar_lotes"]
    assert login(blocked, "operator").status_code == 200
    item = next(item for item in review(blocked).json()["items"] if item["number"] == "SEGUNDO")
    assert item["can_reactivate"] is False
    assert reactivate(blocked).status_code == 403
    assert_unchanged(blocked)


def test_origin_worker_cannot_review_or_reactivate_destination(blocked):
    assert login(blocked, "manager").status_code == 200
    assert review(blocked).status_code == 403
    assert reactivate(blocked).status_code == 403
    assert_unchanged(blocked)


def test_expiration_reached_cannot_be_reactivated(blocked):
    with blocked.factory.begin() as db:
        today = datetime.now(timezone.utc).date()
        db.get(LoteInventario, blocked.late_id).fecha_vencimiento = today
        db.get(LoteInventario, blocked.blocked_lot).fecha_vencimiento = today
        blocked.blocked_expiration = today
    item = next(item for item in review(blocked).json()["items"] if item["number"] == "SEGUNDO")
    assert item["can_reactivate"] is False
    assert reactivate(blocked).status_code == 409
    assert_unchanged(blocked)
