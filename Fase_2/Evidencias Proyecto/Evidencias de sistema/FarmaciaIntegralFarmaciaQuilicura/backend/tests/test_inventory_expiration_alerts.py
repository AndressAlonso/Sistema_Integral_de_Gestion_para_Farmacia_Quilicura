"""E3-H4: límites de vencimiento y consulta, sin acceso a PostgreSQL."""

from contextlib import nullcontext
from datetime import date, timedelta
from types import SimpleNamespace
from unittest.mock import Mock
from uuid import uuid4

import pytest
from app.inventory.repository import PostgresInventoryRepository

TODAY = date(2026, 12, 31)
CASES = [
    (-1, "VENCIDO"), (0, "VENCIDO"), (1, "CRITICO"),
    (15, "CRITICO"), (16, "PROXIMO"), (30, "PROXIMO"),
    (31, "SEGUIMIENTO"), (60, "SEGUIMIENTO"), (61, "SEGUIMIENTO"),
]


def make_lot(days):
    inventory = SimpleNamespace(
        id=uuid4(), producto_id=uuid4(), sucursal_id=uuid4(),
        producto=SimpleNamespace(nombre="Producto", sku="SKU"),
        sucursal=SimpleNamespace(nombre="Sucursal", codigo="SUC"),
    )
    return SimpleNamespace(
        id=uuid4(), inventario=inventory, numero_lote=f"L-{days}",
        fecha_vencimiento=TODAY + timedelta(days=days), cantidad=5,
    )


@pytest.mark.parametrize("days,expected", CASES)
def test_expiration_classification_boundaries(days, expected):
    record = PostgresInventoryRepository._expiration_alert_record(
        make_lot(days), TODAY,
    )
    assert record["days_remaining"] == days
    assert record["alert_level"] == expected


@pytest.mark.parametrize("period", [1, 15, 30])
def test_exclude_expired_query_excludes_today_and_respects_period(period):
    # Inspecciona el SELECT real sin abrir conexiones ni escribir datos.
    candidates = [make_lot(days) for days in (-1, 0, 1, period, period + 1)]
    db = Mock()

    def select_lots(query):
        compiled = query.compile()
        sql = str(compiled)
        assert "lote_inventario.fecha_vencimiento > " in sql
        assert "lote_inventario.fecha_vencimiento >= " not in sql
        assert "lote_inventario.fecha_vencimiento <= " in sql
        dates = [value for value in compiled.params.values() if isinstance(value, date)]
        assert sorted(dates) == [TODAY, TODAY + timedelta(days=period)]
        lower, upper = sorted(dates)
        selected = [lot for lot in candidates if lower < lot.fecha_vencimiento <= upper]
        return SimpleNamespace(unique=lambda: SimpleNamespace(all=lambda: selected))

    db.scalars.side_effect = select_lots
    repository = PostgresInventoryRepository(lambda: nullcontext(db))
    records = repository.list_expiration_alerts(
        days=period, include_expired=False, today=TODAY,
    )
    remaining = [record["days_remaining"] for record in records]
    assert -1 not in remaining
    assert 0 not in remaining
    assert 1 in remaining
    assert period in remaining
    assert period + 1 not in remaining
    db.scalars.assert_called_once()
