from datetime import datetime, timedelta, timezone
from secrets import token_urlsafe

import jwt

COOKIE_NAME = "sigfq_customer_session"
COOKIE_PATH = "/api/customers"


def cookie_options(settings):
    return {"path": COOKIE_PATH, "httponly": True, "secure": settings.cookie_secure, "samesite": "strict"}


def clear_customer_cookie(response, settings):
    response.delete_cookie(COOKIE_NAME, **cookie_options(settings))


def create_customer_token(customer_id, settings):
    now = datetime.now(timezone.utc)
    expires = now + timedelta(minutes=settings.access_token_expire_minutes)
    token = jwt.encode(
        {"sub": str(customer_id), "jti": token_urlsafe(32), "iat": now, "exp": expires,
         "iss": "sigfq", "aud": "sigfq-customers"},
        settings.jwt_secret_key.get_secret_value(), algorithm=settings.jwt_algorithm,
    )
    return token, expires


def validate_customer_token(token, settings):
    return jwt.decode(
        token, settings.jwt_secret_key.get_secret_value(), algorithms=[settings.jwt_algorithm],
        issuer="sigfq", audience="sigfq-customers",
        options={"require": ["sub", "jti", "iat", "exp", "iss", "aud"]},
    )
