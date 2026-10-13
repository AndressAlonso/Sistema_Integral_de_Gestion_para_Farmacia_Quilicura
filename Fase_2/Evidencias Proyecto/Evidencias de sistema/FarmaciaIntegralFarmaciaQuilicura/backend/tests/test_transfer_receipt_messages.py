"""Mensajes de recepción precisos; mismas validaciones y rollback PostgreSQL."""
from datetime import timedelta
from uuid import UUID

import pytest
from sqlalchemy import func, select
from test_auth import login
from test_transfers import (  # noqa: F401
    change,
    destination_inventory,
    stocks,
    transfer,
    transit,
)

from app.models import (
    InventarioSucursal,
    LoteInventario,
    MovimientoInventario,
    Transferencia,
)


@pytest.mark.parametrize("active,different_date", [(False, False), (True, True), (False, True)])
def test_receipt_reports_exact_cause_without_partial_changes(transfer, active, different_date):  # noqa: F811
    transit(transfer)
    with transfer.factory.begin() as db:
        source = db.get(LoteInventario, transfer.late_id)
        inv = InventarioSucursal(producto_id=transfer.product_id, sucursal_id=transfer.destination_id,
                                 stock_fisico=0, stock_reservado=0)
        db.add(inv)
        db.flush()
        destination = LoteInventario(inventario_sucursal_id=inv.id, numero_lote=source.numero_lote,
            fecha_vencimiento=source.fecha_vencimiento + timedelta(days=1 if different_date else 0),
            cantidad=0, activo=active)
        db.add(destination)
        db.flush()
        inventory_id, lot_id = inv.id, destination.id
        source_date, destination_date = source.fecha_vencimiento, destination.fecha_vencimiento
        before_movements = db.scalar(select(func.count()).select_from(MovimientoInventario))
    before_source = stocks(transfer)
    assert login(transfer, "operator").status_code == 200
    response = change(transfer, "receive", {"items": transfer.payload["items"]})
    assert response.status_code == 409
    message = response.json()["detail"]
    assert "SEGUNDO" in message and "Destino QA" in message
    assert ("está deshabilitado" in message) is (not active)
    assert ("vencimiento distinto" in message) is different_date
    if different_date:
        assert source_date.strftime("%d/%m/%Y") in message
        assert destination_date.strftime("%d/%m/%Y") in message
    assert "sigue en tránsito" in message and "no se incorporaron unidades" in message
    with transfer.factory() as db:
        row = db.get(Transferencia, UUID(transfer.payload["request_id"]))
        assert row.estado == "EN_TRANSITO"
        assert db.get(InventarioSucursal, inventory_id).stock_fisico == 0
        lot = db.get(LoteInventario, lot_id)
        assert lot.cantidad == 0 and lot.activo is active
        assert lot.fecha_vencimiento == destination_date
        # El primer lote pudo procesarse antes del conflicto: también se revierte.
        assert db.scalar(select(func.count()).select_from(LoteInventario)
                         .where(LoteInventario.inventario_sucursal_id == inventory_id)) == 1
        assert db.scalar(select(func.count()).select_from(MovimientoInventario)) == before_movements
    assert stocks(transfer) == before_source


def test_quantity_message_reports_expected_and_received(transfer):  # noqa: F811
    transit(transfer)
    assert login(transfer, "operator").status_code == 200
    response = change(transfer, "receive", {"items": [{"product_id": str(transfer.product_id), "quantity": 7}]})
    assert response.status_code == 409
    message = response.json()["detail"]
    assert "Se esperaban 8 unidades" in message and "registraste 7" in message
    assert "sigue en tránsito" in message and "no se incorporaron unidades" in message
    with transfer.factory() as db:
        assert destination_inventory(db, transfer) is None
        assert db.get(Transferencia, UUID(transfer.payload["request_id"])).estado == "EN_TRANSITO"
