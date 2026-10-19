"""E4: conflictos de destino antes de reservar o despachar, con rollback."""
from datetime import timedelta
from uuid import UUID

import pytest
from sqlalchemy import func, select
from test_transfers import change, create, stocks, transfer  # noqa: F401

from app.models import (
    InventarioSucursal,
    LoteInventario,
    MovimientoInventario,
    Transferencia,
)


def add_destination(ctx, active=True, different=False):
    with ctx.factory.begin() as db:
        source = db.get(LoteInventario, ctx.late_id)
        inv = InventarioSucursal(producto_id=ctx.product_id, sucursal_id=ctx.destination_id,
                                 stock_fisico=0, stock_reservado=0)
        db.add(inv)
        db.flush()
        lot = LoteInventario(inventario_sucursal_id=inv.id, numero_lote=source.numero_lote,
                            fecha_vencimiento=source.fecha_vencimiento + timedelta(days=int(different)),
                            cantidad=0, activo=active)
        db.add(lot)
        db.flush()
        return lot.id


def movements(ctx):
    with ctx.factory() as db:
        return db.scalar(select(func.count()).select_from(MovimientoInventario))


@pytest.mark.parametrize("stage", ["create", "dispatch"])
@pytest.mark.parametrize("active,different", [(False, False), (True, True), (False, True)])
def test_conflict_blocks_without_partial_stock_changes(transfer, stage, active, different):  # noqa: F811
    if stage == "dispatch":
        create(transfer)
        assert change(transfer, "approve").status_code == 200
    lot_id = add_destination(transfer, active, different)
    before, before_movements = stocks(transfer), movements(transfer)
    response = (transfer.client.post("/api/transfers", json=transfer.payload)
                if stage == "create" else change(transfer, "dispatch"))
    assert response.status_code == 409, response.text
    text = response.json()["detail"]
    assert "SEGUNDO" in text and "Destino QA" in text and "Inventario" in text
    assert ("deshabilitado" in text) is (not active)
    assert ("vencimiento distinto" in text) is different
    assert stocks(transfer) == before
    assert movements(transfer) == before_movements
    with transfer.factory() as db:
        row = db.get(Transferencia, UUID(transfer.payload["request_id"]))
        assert (row is None) if stage == "create" else (row.estado == "AUTORIZADA")
        assert db.get(LoteInventario, lot_id).cantidad == 0
        assert db.get(LoteInventario, transfer.early_id).cantidad == 5
        assert db.get(LoteInventario, transfer.late_id).cantidad == 15
    if stage == "dispatch":
        assert change(transfer, "reject", {"reason": "Conflicto destino"}).status_code == 200
        assert stocks(transfer) == (20, 0, 20)


def test_active_empty_destination_is_compatible(transfer):  # noqa: F811
    add_destination(transfer)
    create(transfer)
    assert change(transfer, "approve").status_code == 200
    assert change(transfer, "dispatch").status_code == 200
