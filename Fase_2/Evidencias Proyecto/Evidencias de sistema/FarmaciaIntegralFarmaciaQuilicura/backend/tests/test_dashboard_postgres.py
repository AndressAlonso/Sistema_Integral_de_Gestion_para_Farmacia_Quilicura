"""Verificación adicional en PostgreSQL local con rollback (opt-in)."""
from datetime import datetime, timezone
from decimal import Decimal
from uuid import uuid4

from test_audit import allow_audit
from test_auth import login

from app.models import SesionCaja, Venta


def test_dashboard_postgres_chile_period_and_branch(setup):
    allow_audit(setup, "SOCIO")
    login(setup)
    with setup.factory.begin() as db:
        cash = SesionCaja(
            usuario_id=setup.ids["admin"], sucursal_id=setup.ids["branch"],
            monto_inicial=Decimal(0),
        )
        db.add(cash)
        db.flush()
        for hour, amount in ((2, 900), (3, 100), (23, 200)):
            db.add(Venta(
                id=uuid4(), solicitud_hash="a" * 64, sesion_caja_id=cash.id,
                usuario_id=setup.ids["admin"], sucursal_id=setup.ids["branch"],
                fecha=datetime(2026, 1, 10, hour, tzinfo=timezone.utc),
                medio_pago="EFECTIVO", subtotal=Decimal(amount), descuento=Decimal(0),
                total=Decimal(amount),
            ))
    query = f"/api/dashboard?branch_id={setup.ids['branch']}&date_from=2026-01-10&date_to=2026-01-10"
    response = setup.client.get(query)
    assert response.status_code == 200, response.text
    result = response.json()
    assert result["sales"]["total"] == "300.00"
    assert result["sales"]["count"] == 2
    assert result["daily"] == [{"date": "2026-01-10", "total": "300.00", "count": 2}]
    assert result["payments"] == [{"method": "EFECTIVO", "total": "300.00", "count": 2}]
    assert setup.client.get(query.replace(str(setup.ids["branch"]), str(uuid4()))).json()["sales"]["count"] == 0
