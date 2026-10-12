"""Precio vigente compartido por catálogo online y carrito; motor único E2-H3."""
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel

from app.pos.pricing import best_price, money


class AppliedPromotion(BaseModel):
    code: str
    name: str
    kind: Literal["PERCENT", "FIXED_PRICE"]
    value: Decimal


def calculate_price(product, promotions, now):
    final, chosen = best_price(product.precio_actual, product.id, product.categoria_id, now, promotions)
    base = money(product.precio_actual)
    return {"base_price": base, "price": final, "discount": money(base - final),
            "promotion": AppliedPromotion(**chosen) if chosen else None}
