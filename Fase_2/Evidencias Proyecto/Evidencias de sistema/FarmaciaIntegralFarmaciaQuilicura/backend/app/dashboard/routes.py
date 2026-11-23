from datetime import date, datetime, timedelta, timezone
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request

from app.auth.routes import authenticated_user
from app.business_time import BUSINESS_TIMEZONE as CHILE
from app.business_time import business_date
from app.dashboard.service import dashboard

router = APIRouter(prefix="/api/dashboard", tags=["Indicadores"])


def period(date_from: date | None, date_to: date | None, today: date):
    end = date_to or today
    start = date_from or end.replace(day=1)
    if start > end:
        raise HTTPException(422, "La fecha inicial no puede ser posterior a la fecha final.")
    if (end - start).days > 365 or end == date.max:
        raise HTTPException(422, "Selecciona un período de hasta 366 días.")
    return start, end


@router.get("")
def get_dashboard(
    request: Request,
    authenticated: Annotated[tuple, Depends(authenticated_user)],
    branch_id: UUID | None = None,
    date_from: date | None = None,
    date_to: date | None = None,
):
    actor, _ = authenticated
    if not {"ADMINISTRADOR", "SOCIO"}.intersection(actor.roles):
        raise HTTPException(403, "No tienes permiso para consultar los indicadores.")
    today = business_date()
    start, end = period(date_from, date_to, today)
    # Límites locales inclusivos, incluso en cambios de horario de verano.
    since = datetime.combine(start, datetime.min.time(), CHILE).astimezone(timezone.utc)
    until = datetime.combine(end + timedelta(days=1), datetime.min.time(), CHILE).astimezone(timezone.utc)
    with request.app.state.users.session_factory() as db:
        return dashboard(db, branch_id, start, end, since, until, today)
