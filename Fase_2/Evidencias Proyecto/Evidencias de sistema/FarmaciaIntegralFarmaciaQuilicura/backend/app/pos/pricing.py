"""Cálculo E5-H2. El proveedor de E2-H3 podrá sustituir la colección recibida."""

from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import ROUND_HALF_UP, Decimal
from typing import Literal
from uuid import UUID


def money(value: Decimal) -> Decimal:
    return value.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


@dataclass(frozen=True)
class Promotion:
    code: str
    name: str
    kind: Literal["PERCENT", "FIXED_PRICE"]
    value: Decimal
    starts_at: datetime
    ends_at: datetime
    product_id: UUID | None = None
    category_id: UUID | None = None

    def applies(self, product_id: UUID, category_id: UUID, now: datetime) -> bool:
        return (
            self.starts_at <= now < self.ends_at
            and (self.product_id is not None or self.category_id is not None)
            and (self.product_id is None or self.product_id == product_id)
            and (self.category_id is None or self.category_id == category_id)
            and self.value >= 0
            and (self.kind != "PERCENT" or self.value <= 100)
        )


def best_price(
    base: Decimal,
    product_id: UUID,
    category_id: UUID,
    now: datetime,
    promotions: tuple[Promotion, ...] = (),
):
    """No acumular descuentos; desempatar por código para resultados estables."""
    result = money(base)
    selected = None
    for promo in sorted(promotions, key=lambda item: item.code):
        if not promo.applies(product_id, category_id, now):
            continue
        candidate = money(
            base * (1 - promo.value / 100) if promo.kind == "PERCENT" else promo.value
        )
        if candidate < result:
            result = candidate
            selected = {
                "code": promo.code,
                "name": promo.name,
                "kind": promo.kind,
                "value": str(promo.value),
            }
    return result, selected


def development_promotions(settings):
    if (
        settings.app_environment != "development"
        or settings.pos_demo_product_id is None
    ):
        return ()
    return (
        Promotion(
            "DEMO-E5-20",
            "Demostración: 20% de descuento",
            "PERCENT",
            Decimal(20),
            datetime(2026, 1, 1, tzinfo=timezone.utc),
            datetime(2030, 1, 1, tzinfo=timezone.utc),
            product_id=settings.pos_demo_product_id,
        ),
    )
