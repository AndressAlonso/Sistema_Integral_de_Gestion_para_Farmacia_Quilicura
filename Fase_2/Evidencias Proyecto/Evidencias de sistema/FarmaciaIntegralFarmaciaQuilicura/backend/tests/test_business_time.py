from datetime import date, datetime, timezone
from uuid import uuid4

import pytest
from app import business_time
from app.business_time import business_date
from app.inventory.schemas import CreateInventoryLot
from app.models import LoteInventario
from app.pos.service import PosService
from pydantic import ValidationError
from sqlalchemy import select
from test_pos import pos  # noqa: F401
from test_transfers import transfer  # noqa: F401


@pytest.mark.parametrize("instant,expected", [
    ("2026-11-06T01:30:00+00:00", date(2026, 11, 5)),
    ("2026-11-06T02:59:59+00:00", date(2026, 11, 5)),
    ("2026-11-06T03:00:00+00:00", date(2026, 11, 6)),
    ("2026-07-06T03:59:59+00:00", date(2026, 7, 5)),
    ("2026-07-06T04:00:00+00:00", date(2026, 7, 6)),
])
def test_business_day_follows_chile_in_summer_and_winter(instant, expected):
    assert business_date(datetime.fromisoformat(instant)) == expected


def test_business_day_requires_an_unambiguous_instant():
    with pytest.raises(ValueError):
        business_date(datetime(2026, 11, 6))  # noqa: DTZ001 -- entrada inválida deliberada


@pytest.mark.parametrize("hour,expected_day,vendible", [(1, 5, True), (3, 6, False)])
def test_lot_validation_and_pos_agree_at_chilean_midnight(pos, monkeypatch, hour, expected_day, vendible):  # noqa: F811 -- fixture importada
    instant = datetime(2026, 11, 6, hour, 30, tzinfo=timezone.utc)

    class Clock(datetime):
        @classmethod
        def now(cls, tz=None):
            return instant.astimezone(tz or timezone.utc)

    monkeypatch.setattr(business_time, "datetime", Clock)
    assert business_date() == date(2026, 11, expected_day)
    with pos.factory.begin() as db:
        for lot in db.scalars(select(LoteInventario).where(LoteInventario.inventario_sucursal_id == pos.inventory_id)):
            lot.fecha_vencimiento = date(2026, 11, 6)
    with pos.factory() as db:
        _, _, available = PosService.availability(db, pos.product_id, pos.ids["branch"])
    assert (available > 0) == vendible
    data = {"inventory_id": uuid4(), "lot_number": "QA-MEDIANOCHE", "expiration_date": date(2026, 11, 6), "quantity": 1}
    if vendible:
        assert CreateInventoryLot(**data).expiration_date == date(2026, 11, 6)
    else:
        with pytest.raises(ValidationError):
            CreateInventoryLot(**data)
