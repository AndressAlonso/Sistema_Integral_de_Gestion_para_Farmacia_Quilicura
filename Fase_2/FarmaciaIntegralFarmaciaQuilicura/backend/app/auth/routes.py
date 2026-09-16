from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException, Request, Response
from jwt import InvalidTokenError
from pydantic import BaseModel, EmailStr, Field, field_validator

from app.auth.security import create_token, dummy_hash, validate_token, verify_password
from app.auth.state import LoginLimited

router = APIRouter(prefix="/api/auth", tags=["auth"])
COOKIE_NAME = "sigfq_session"


class LoginRequest(BaseModel):
    email: EmailStr = Field(max_length=254)
    password: str = Field(min_length=1, max_length=1024)

    @field_validator("email", mode="before")
    @classmethod
    def trim_email(cls, value: object) -> object:
        return value.strip() if isinstance(value, str) else value


class PublicUser(BaseModel):
    id: int
    email: EmailStr


class SessionResponse(BaseModel):
    user: PublicUser
    expires_at: datetime


def check_origin(request: Request):
    origin = request.headers.get("origin")
    if origin and origin not in request.app.state.settings.cors_origins:
        raise HTTPException(403, "Solicitud no permitida.")


def too_many_attempts(seconds: int):
    raise HTTPException(
        429,
        "Demasiados intentos de inicio de sesión. Espera antes de intentar nuevamente.",
        headers={"Retry-After": str(seconds)},
    )


@router.post("/login", response_model=SessionResponse)
def login(data: LoginRequest, request: Request, response: Response) -> SessionResponse:
    settings = request.app.state.settings
    check_origin(request)
    email = str(data.email).lower()
    ip = request.client.host if request.client else "unknown"
    auth = request.app.state.auth
    try:
        ticket = auth.begin_login(email, ip)
    except LoginLimited as exc:
        too_many_attempts(exc.seconds)
    user = request.app.state.users.by_email(str(data.email))
    valid_password = verify_password(
        data.password, user.password_hash if user else dummy_hash
    )
    success = valid_password and user is not None and user.is_active
    wait = auth.finish_login(email, ip, ticket, success)
    if not success:
        if wait:
            too_many_attempts(wait)
        raise HTTPException(401, "Correo o contraseña incorrectos.")
    token, expires = create_token(user.id, settings)
    claims = validate_token(token, settings)
    auth.register_session(claims["jti"], claims["exp"])
    response.set_cookie(
        COOKIE_NAME,
        token,
        httponly=True,
        secure=settings.cookie_secure,
        samesite="strict",
        path="/api/auth",
        max_age=settings.access_token_expire_minutes * 60,
    )
    return SessionResponse(
        user=PublicUser(id=user.id, email=user.email), expires_at=expires
    )


@router.get("/me", response_model=SessionResponse)
def me(request: Request) -> SessionResponse:
    token = request.cookies.get(COOKIE_NAME)
    try:
        claims = validate_token(token or "", request.app.state.settings)
        user_id = int(claims["sub"])
    except (InvalidTokenError, ValueError, TypeError, KeyError):
        raise HTTPException(401, "La sesión no es válida o expiró.") from None
    if not request.app.state.auth.session_active(claims["jti"]):
        raise HTTPException(401, "La sesión no es válida o expiró.")
    user = request.app.state.users.by_id(user_id)
    if user is None or not user.is_active:
        raise HTTPException(401, "La sesión no es válida o expiró.")
    return SessionResponse(
        user=PublicUser(id=user.id, email=user.email),
        expires_at=datetime.fromtimestamp(claims["exp"], timezone.utc),
    )


@router.post("/logout", status_code=204)
def logout(request: Request) -> Response:
    check_origin(request)
    try:
        claims = validate_token(
            request.cookies.get(COOKIE_NAME, ""), request.app.state.settings
        )
        request.app.state.auth.revoke_session(claims["jti"])
    except (InvalidTokenError, ValueError, TypeError, KeyError):
        pass
    response = Response(status_code=204)
    response.delete_cookie(
        COOKIE_NAME,
        path="/api/auth",
        httponly=True,
        secure=request.app.state.settings.cookie_secure,
        samesite="strict",
    )
    return response
