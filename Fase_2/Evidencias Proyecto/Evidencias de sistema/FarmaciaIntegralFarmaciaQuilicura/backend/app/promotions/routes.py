from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request

from app.auth.routes import authenticated_user, check_origin
from app.auth.users import User
from app.promotions.schemas import PromotionInput, PromotionResponse

router = APIRouter(prefix="/api/promotions", tags=["Promociones — E2-H3"])


def manager(request: Request) -> User:
    actor, _ = authenticated_user(request)
    if "ADMINISTRADOR" not in actor.roles or "catalogo.gestionar" not in actor.permissions:
        raise HTTPException(403, "Solo un administrador autorizado puede gestionar promociones.")
    return actor


Actor = Annotated[User, Depends(manager)]


@router.get("", response_model=list[PromotionResponse])
def list_promotions(request: Request, actor: Actor):
    return request.app.state.promotions.list()


@router.post("", response_model=PromotionResponse, status_code=201)
def create_promotion(data: PromotionInput, request: Request, actor: Actor):
    check_origin(request)
    return request.app.state.promotions.save(data, actor)


@router.patch("/{promotion_id}", response_model=PromotionResponse)
def update_promotion(promotion_id: UUID, data: PromotionInput, request: Request, actor: Actor):
    check_origin(request)
    return request.app.state.promotions.save(data, actor, promotion_id)
