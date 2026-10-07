from fastapi import APIRouter, HTTPException, Request

from app.ecommerce.cart.service import CartService
from app.ecommerce.guest.schemas import GuestValidationRequest, GuestValidationResponse

router = APIRouter(prefix="/api/ecommerce/guest", tags=["ecommerce-guest"])


@router.post("/validate", response_model=GuestValidationResponse)
def validate(data: GuestValidationRequest, request: Request):
    origin = request.headers.get("origin")
    if origin and origin not in request.app.state.settings.cors_origins:
        raise HTTPException(403, "Solicitud no permitida.")
    # No consulta clientes ni sesiones: el correo no vincula una identidad.
    cart = CartService(request.app.state.cart).validate(data.cart)
    return GuestValidationResponse(guest=data.guest, cart=cart)
