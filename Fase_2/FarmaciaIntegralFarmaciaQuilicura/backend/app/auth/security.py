from datetime import datetime, timedelta, timezone
from secrets import token_urlsafe

import jwt
from pwdlib import PasswordHash
from pwdlib.exceptions import UnknownHashError

from app.config import Settings

password_hasher = PasswordHash.recommended()
# También realizar Argon2 cuando el correo no exista.
dummy_hash = password_hasher.hash(token_urlsafe(32))


def verify_password(password: str, password_hash: str) -> bool:
    try:
        return password_hasher.verify(password, password_hash)
    except (ValueError, UnknownHashError):
        return False


def create_token(user_id: int, settings: Settings) -> tuple[str, datetime]:
    now = datetime.now(timezone.utc)
    expires = now + timedelta(minutes=settings.access_token_expire_minutes)
    token = jwt.encode(
        {
            "sub": str(user_id),
            "jti": token_urlsafe(32),
            "iat": now,
            "exp": expires,
            "iss": "sigfq",
            "aud": "sigfq-internal",
        },
        settings.jwt_secret_key.get_secret_value(),
        algorithm=settings.jwt_algorithm,
    )
    return token, expires


def validate_token(token: str, settings: Settings) -> dict:
    return jwt.decode(
        token,
        settings.jwt_secret_key.get_secret_value(),
        algorithms=[settings.jwt_algorithm],
        issuer="sigfq",
        audience="sigfq-internal",
        options={"require": ["sub", "jti", "iat", "exp", "iss", "aud"]},
    )
