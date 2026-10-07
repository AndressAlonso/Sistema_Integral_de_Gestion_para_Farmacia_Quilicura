from fastapi import APIRouter, Request

from app.ecommerce.cart.schemas import CartRequest, CartResponse
from app.ecommerce.cart.service import CartService

router = APIRouter(prefix="/api/ecommerce/cart", tags=["ecommerce-cart"])


@router.post("/validate", response_model=CartResponse)
def validate(data: CartRequest, request: Request):
    return CartService(request.app.state.cart).validate(data)
