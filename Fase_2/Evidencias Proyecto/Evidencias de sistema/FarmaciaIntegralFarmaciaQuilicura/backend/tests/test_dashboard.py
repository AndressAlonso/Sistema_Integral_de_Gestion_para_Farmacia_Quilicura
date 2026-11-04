"""E9: consultas reales sobre un almacén efímero, sin tocar datos locales.

SQLite solo se usa como doble de almacenamiento para estas pruebas de agregación.
timezone() reproduce la conversión chilena de PostgreSQL; producción sigue usando
PostgreSQL. Las tablas reducidas no prueban constraints ni migraciones.
"""
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from types import SimpleNamespace
from uuid import uuid4
from zoneinfo import ZoneInfo

import pytest
from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient
from sqlalchemy import Column, MetaData, Table, create_engine, event
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.auth.routes import authenticated_user
from app.dashboard.routes import period, router
from app.dashboard.service import dashboard
from app.models import Base

TODAY = date(2026, 1, 10)
FIELDS = {
    "sucursal": "id nombre",
    "producto": "id nombre activo",
    "venta": "id sucursal_id fecha total medio_pago",
    "venta_detalle": "id venta_id producto_id cantidad",
    "reversa_venta": "id venta_id fecha importe",
    "inventario_sucursal": "id producto_id sucursal_id stock_fisico stock_reservado stock_minimo",
    "lote_inventario": "id inventario_sucursal_id numero_lote fecha_vencimiento cantidad activo",
    "movimiento_inventario": "id inventario_sucursal_id tipo cantidad_fisica cantidad_reservada creado_en",
}


@pytest.fixture
def store():
    engine = create_engine("sqlite://", poolclass=StaticPool,
                           connect_args={"check_same_thread": False})

    @event.listens_for(engine, "connect")
    def timezone_function(connection, _):
        # Retornar la fecha/hora local SIN offset para que date() no la reconvierta.
        def local_time(zone, value):
            return datetime.fromisoformat(value).replace(tzinfo=timezone.utc).astimezone(
                ZoneInfo(zone),
            ).replace(tzinfo=None).isoformat(sep=" ")
        connection.create_function("timezone", 2, local_time)

    metadata = MetaData()
    tables = {
        name: Table(name, metadata, *[
            Column(field, Base.metadata.tables[name].c[field].type)
            for field in fields.split()
        ]) for name, fields in FIELDS.items()
    }
    metadata.create_all(engine)
    factory = sessionmaker(engine)
    ids = {name: uuid4() for name in ("b1", "b2", "p1", "p2", "i1", "i2")}

    def add(name, **values):
        values.setdefault("id", uuid4())
        with factory.begin() as db:
            db.execute(tables[name].insert().values(**values))
        return values["id"]

    for key in ("b1", "b2"):
        add("sucursal", id=ids[key], nombre=key)
    for key in ("p1", "p2"):
        add("producto", id=ids[key], nombre=key, activo=True)
    for suffix in ("1", "2"):
        add("inventario_sucursal", id=ids["i" + suffix], producto_id=ids["p" + suffix],
            sucursal_id=ids["b" + suffix], stock_fisico=12, stock_reservado=2, stock_minimo=10)
    yield SimpleNamespace(factory=factory, ids=ids, add=add)
    engine.dispose()


def metrics(store, branch=None, start=TODAY, end=TODAY):
    chile = ZoneInfo("America/Santiago")
    since = datetime.combine(start, datetime.min.time(), chile).astimezone(timezone.utc)
    until = datetime.combine(end + timedelta(days=1), datetime.min.time(), chile).astimezone(timezone.utc)
    with store.factory() as db:
        return dashboard(db, branch, start, end, since, until, TODAY)


def sale(store, amount, branch="b1", at="2026-01-10T12:00:00+00:00", method="EFECTIVO"):
    return store.add("venta", sucursal_id=store.ids[branch],
                     fecha=datetime.fromisoformat(at), total=Decimal(amount), medio_pago=method)


def test_totals_do_not_multiply_details_and_count_online_once(store):
    first = sale(store, "1000")
    second = sale(store, "500", method="MERCADOPAGO")
    sale(store, "300", branch="b2")
    for sale_id, product, quantity in ((first, "p1", 2), (first, "p2", 1), (second, "p1", 3)):
        store.add("venta_detalle", venta_id=sale_id, producto_id=store.ids[product], cantidad=quantity)
    result = metrics(store)
    assert result["sales"] == {"total": "1800.00", "count": 3, "average": "600.00",
                               "returns": "0.00", "net": "1800.00"}
    assert result["top_products"][0]["quantity"] == 5
    assert sum(Decimal(item["total"]) for item in result["payments"]) == Decimal(1800)
    assert metrics(store, store.ids["b1"])["sales"]["count"] == 2
    assert len(metrics(store, store.ids["b1"])["by_branch"]) == 1


def test_chile_boundaries_inclusive_and_zero_filled_days(store):
    sale(store, "999", at="2026-01-10T02:59:59+00:00")  # 9 enero
    sale(store, "100", at="2026-01-10T03:00:00+00:00")
    sale(store, "200", at="2026-01-11T02:59:59+00:00")
    sale(store, "999", at="2026-01-11T03:00:00+00:00")  # 11 enero
    result = metrics(store)
    assert result["daily"] == [{"date": "2026-01-10", "total": "300.00", "count": 2}]
    empty = metrics(store, start=date(2026, 2, 1), end=date(2026, 2, 3))
    assert len(empty["daily"]) == 3
    assert all(row["total"] == "0.00" for row in empty["daily"])
    assert empty["sales"]["average"] == "0.00"


def test_returns_use_operation_date_and_original_branch(store):
    old_sale = sale(store, "1000", at="2026-01-01T12:00:00+00:00")
    store.add("reversa_venta", venta_id=old_sale, importe=Decimal(400),
              fecha=datetime(2026, 1, 10, 12, tzinfo=timezone.utc))
    result = metrics(store, store.ids["b1"])
    assert result["sales"]["total"] == "0.00"
    assert result["sales"]["returns"] == "400.00"
    assert result["sales"]["net"] == "-400.00"
    assert metrics(store, store.ids["b2"])["sales"]["returns"] == "0.00"


def test_current_low_stock_uses_available_and_expiration_limits(store):
    for days, quantity, active in ((0, 5, True), (1, 5, True), (15, 5, True),
                                    (16, 5, True), (30, 5, True), (31, 5, True),
                                    (7, 0, True), (8, 5, False)):
        store.add("lote_inventario", inventario_sucursal_id=store.ids["i1"],
                  numero_lote=str(days), fecha_vencimiento=TODAY + timedelta(days=days),
                  cantidad=quantity, activo=active)
    result = metrics(store, store.ids["b1"])["inventory"]
    assert result["low_count"] == 1  # 12 físicos - 2 reservados == mínimo 10
    assert result["low_stock"][0]["available"] == 10
    assert result["expiring_count"] == 4
    assert result["expired_count"] == 1
    assert [row["days"] for row in result["expiring"]] == [1, 15, 16, 30]
    assert metrics(store, store.ids["b2"])["inventory"]["expiring_count"] == 0
    assert metrics(store, start=date(2025, 1, 1))["inventory"]["as_of"] == TODAY.isoformat()


def test_movements_apply_period_and_branch_without_mixing_stock_snapshot(store):
    for inventory, at, quantity in (("i1", 10, -3), ("i1", 9, -9), ("i2", 10, -7)):
        store.add("movimiento_inventario", inventario_sucursal_id=store.ids[inventory],
                  tipo="VENTA", cantidad_fisica=quantity, cantidad_reservada=0,
                  creado_en=datetime(2026, 1, at, 12, tzinfo=timezone.utc))
    assert metrics(store, store.ids["b1"])["movements"] == [
        {"type": "VENTA", "count": 1, "physical": -3, "reserved": 0},
    ]


@pytest.mark.parametrize("role,expected", [("SOCIO", 200), ("ADMINISTRADOR", 200), ("CAJERO", 403)])
def test_endpoint_authorization_and_validation(store, role, expected):
    app = FastAPI()
    app.include_router(router)
    app.state.users = SimpleNamespace(session_factory=store.factory)
    app.dependency_overrides[authenticated_user] = lambda: (SimpleNamespace(roles=[role]), {})
    with TestClient(app) as client:
        assert client.get("/api/dashboard").status_code == expected
        if expected == 200:
            for query in ("date_from=oops", "branch_id=oops",
                          "date_from=2026-02-01&date_to=2026-01-01",
                          "date_from=2024-01-01&date_to=2026-01-01"):
                assert client.get("/api/dashboard?" + query).status_code == 422
            assert client.get("/api/dashboard?branch_id=" + str(uuid4())).json()["sales"]["count"] == 0


def test_endpoint_requires_session_before_queries():
    app = FastAPI()
    app.include_router(router)
    def anonymous():
        raise HTTPException(401, "Sesión requerida")
    app.dependency_overrides[authenticated_user] = anonymous
    with TestClient(app) as client:
        assert client.get("/api/dashboard").status_code == 401


def test_default_period_and_maximum_date():
    assert period(None, None, TODAY) == (date(2026, 1, 1), TODAY)
    assert period(None, date(2025, 12, 20), TODAY) == (date(2025, 12, 1), date(2025, 12, 20))
    with pytest.raises(HTTPException):
        period(date.max, date.max, TODAY)
