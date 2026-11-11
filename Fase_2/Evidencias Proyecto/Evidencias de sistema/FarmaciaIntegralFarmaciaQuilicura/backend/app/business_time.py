"""Fecha de negocio común para lotes y operaciones de la farmacia en Chile."""
from datetime import date, datetime, timezone
from zoneinfo import ZoneInfo

BUSINESS_TIMEZONE = ZoneInfo("America/Santiago")


def business_date(instant: datetime | None = None) -> date:
    instant = instant if instant is not None else datetime.now(timezone.utc)
    if instant.tzinfo is None:
        raise ValueError("La fecha de negocio requiere un instante con zona horaria.")
    return instant.astimezone(BUSINESS_TIMEZONE).date()
