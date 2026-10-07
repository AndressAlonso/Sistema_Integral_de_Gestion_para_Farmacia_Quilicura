from datetime import datetime, timezone
from uuid import UUID

from fastapi import APIRouter, HTTPException, Request, Response
from jwt import InvalidTokenError

from app.customers.schemas import (
    LoginRequest,
    PublicCustomer,
    RegisterRequest,
    SessionResponse,
)
from app.customers.security import (
    COOKIE_NAME,
    clear_customer_cookie,
    cookie_options,
    create_customer_token,
    validate_customer_token,
)
from app.customers.service import (
    public_customer,
    register_customer,
    verify_customer_login,
)

router = APIRouter(prefix="/api/customers", tags=["customers"])


def check_origin(request):
    origin = request.headers.get("origin")
    if origin and origin not in request.app.state.settings.cors_origins:
        raise HTTPException(403, "Solicitud no permitida.")


@router.post("/register", status_code=201, response_model=PublicCustomer)
def register(data: RegisterRequest, request: Request):
    check_origin(request)
    return register_customer(data, request.app.state.customers)


@router.post("/login", response_model=SessionResponse)
def login(data: LoginRequest, request: Request, response: Response):
    check_origin(request)
    row = verify_customer_login(data, request)
    settings = request.app.state.settings
    token, expires = create_customer_token(row.id, settings)
    if not request.app.state.customer_sessions.register(token, row.id, expires):
        raise HTTPException(401, "Correo o contraseña incorrectos.")
    response.set_cookie(COOKIE_NAME, token, max_age=settings.access_token_expire_minutes * 60,
                        **cookie_options(settings))
    return SessionResponse(customer=public_customer(row), expires_at=expires)


def authenticated_customer(request):
    token = request.cookies.get(COOKIE_NAME, "")
    try:
        claims = validate_customer_token(token, request.app.state.settings)
        customer_id = UUID(claims["sub"])
    except (InvalidTokenError, ValueError, TypeError, KeyError):
        raise HTTPException(401, "La sesión no es válida o expiró.") from None
    if not request.app.state.customer_sessions.active(token, customer_id):
        raise HTTPException(401, "La sesión no es válida o expiró.")
    row = request.app.state.customers.by_id(customer_id)
    if row is None or not row.activo:
        raise HTTPException(401, "La sesión no es válida o expiró.")
    return row, claims


@router.get("/me", response_model=SessionResponse)
def me(request: Request):
    row, claims = authenticated_customer(request)
    return SessionResponse(customer=public_customer(row),
                           expires_at=datetime.fromtimestamp(claims["exp"], timezone.utc))


@router.post("/logout", status_code=204)
def logout(request: Request):
    check_origin(request)
    token = request.cookies.get(COOKIE_NAME, "")
    try:
        validate_customer_token(token, request.app.state.settings)
        request.app.state.customer_sessions.revoke(token)
    except (InvalidTokenError, ValueError, TypeError, KeyError):
        pass
    response = Response(status_code=204)
    clear_customer_cookie(response, request.app.state.settings)
    return response
