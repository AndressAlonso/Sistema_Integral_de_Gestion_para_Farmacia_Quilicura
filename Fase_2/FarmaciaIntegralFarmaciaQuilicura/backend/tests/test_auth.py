from datetime import datetime, timedelta, timezone
from uuid import uuid4

import jwt
import pytest
from conftest import PASSWORD
from fastapi.testclient import TestClient

from app.auth.routes import COOKIE_NAME
from app.auth.security import password_hasher
from app.auth.sessions import SessionRepository
from app.auth.state import AuthState
from app.config import Settings
from app.main import create_app
from app.models import SesionInterna, UsuarioInterno


def login(ctx, name="admin", password=PASSWORD):
    return ctx.client.post(
        "/api/auth/login", json={"email": ctx.emails[name], "password": password}
    )


def test_valid_login_and_private_cookie(setup):
    response = login(setup)
    assert response.status_code == 200
    assert response.json()["user"]["id"] == str(setup.ids["admin"])
    assert "usuarios.gestionar" in response.json()["user"]["permissions"]
    assert "password" not in response.text
    cookie = response.headers["set-cookie"]
    assert (
        "HttpOnly" in cookie and "SameSite=strict" in cookie and "Path=/api;" in cookie
    )
    assert "Max-Age=32400" in cookie
    assert response.headers["cache-control"] == "no-store"
    assert setup.client.get("/api/auth/me").status_code == 200


@pytest.mark.parametrize(
    "name,password",
    [("admin", "incorrecta"), ("inactive", PASSWORD), ("inactive", "incorrecta")],
)
def test_invalid_credentials_generic(setup, name, password):
    response = login(setup, name, password)
    assert response.status_code == 401
    assert response.json() == {"detail": "Correo o contraseña incorrectos."}


def test_unknown_email_same_error(setup):
    response = setup.client.post(
        "/api/auth/login",
        json={"email": f"missing-{setup.suffix}@farmacia.cl", "password": PASSWORD},
    )
    assert response.status_code == 401
    assert response.json() == {"detail": "Correo o contraseña incorrectos."}


def test_email_normalization(setup):
    response = setup.client.post(
        "/api/auth/login",
        json={"email": f" {setup.emails['admin'].upper()} ", "password": PASSWORD},
    )
    assert response.status_code == 200


@pytest.mark.parametrize(
    "token", ["", "invalid", "eyJhbGciOiJub25lIn0.eyJzdWIiOiIxIn0."]
)
def test_no_valid_token(setup, token):
    assert (
        setup.client.get(
            "/api/auth/me", headers={"Cookie": f"{COOKIE_NAME}={token}"}
        ).status_code
        == 401
    )


@pytest.mark.parametrize(
    "variant",
    [
        "expired",
        "signature",
        "missing_exp",
        "audience",
        "unknown_user",
        "bad_subject",
        "algorithm",
        "unregistered",
    ],
)
def test_invalid_token_claims(setup, variant):
    now = datetime.now(timezone.utc)
    claims = {
        "sub": str(setup.ids["admin"]),
        "jti": str(uuid4()),
        "iat": now - timedelta(minutes=2),
        "exp": now + timedelta(minutes=5),
        "iss": "sigfq",
        "aud": "sigfq-internal",
    }
    key = setup.settings.jwt_secret_key.get_secret_value()
    algorithm = "HS256"
    if variant == "expired":
        claims["exp"] = now - timedelta(seconds=1)
    elif variant == "signature":
        key = "other-key-" * 8
    elif variant == "missing_exp":
        del claims["exp"]
    elif variant == "audience":
        claims["aud"] = "other"
    elif variant == "unknown_user":
        claims["sub"] = str(uuid4())
    elif variant == "bad_subject":
        claims["sub"] = "invalid-uuid"
    elif variant == "algorithm":
        algorithm = "HS384"
    token = jwt.encode(claims, key, algorithm=algorithm)
    if variant != "unregistered":
        with setup.factory.begin() as db:
            db.add(
                SesionInterna(
                    usuario_id=setup.ids["admin"],
                    token_hash=SessionRepository.token_hash(token),
                    creada_en=now - timedelta(minutes=5),
                    expira_en=now + timedelta(minutes=5),
                )
            )
    assert (
        setup.client.get(
            "/api/auth/me", headers={"Cookie": f"{COOKIE_NAME}={token}"}
        ).status_code
        == 401
    )


@pytest.mark.parametrize(
    "body",
    [
        {},
        {"email": "bad", "password": PASSWORD},
        {"email": "test@farmacia.cl", "password": ""},
        {"email": "test@farmacia.cl", "password": "x" * 1025},
    ],
)
def test_invalid_body_safe(setup, body):
    response = setup.client.post("/api/auth/login", json=body)
    assert response.status_code == 422
    assert response.json() == {"detail": "Revisa el correo y la contraseña ingresados."}


def test_malformed_json(setup):
    assert (
        setup.client.post(
            "/api/auth/login", content="{", headers={"Content-Type": "application/json"}
        ).status_code
        == 422
    )


def test_logout_revokes_copy_and_is_idempotent(setup):
    login(setup)
    copied = setup.client.cookies.get(COOKIE_NAME)
    assert setup.client.post("/api/auth/logout").status_code == 204
    assert (
        setup.client.get(
            "/api/auth/me", headers={"Cookie": f"{COOKIE_NAME}={copied}"}
        ).status_code
        == 401
    )
    assert setup.client.post("/api/auth/logout").status_code == 204


def test_restart_preserves_active_but_not_revoked_session(setup):
    login(setup)
    token = setup.client.cookies.get(COOKIE_NAME)
    app = create_app(setup.settings, session_factory=setup.factory)
    with TestClient(app) as restarted:
        headers = {"Cookie": f"{COOKIE_NAME}={token}"}
        assert restarted.get("/api/auth/me", headers=headers).status_code == 200
        assert restarted.post("/api/auth/logout", headers=headers).status_code == 204
    assert setup.client.get("/api/auth/me").status_code == 401


def test_logout_only_current_session(setup):
    login(setup)
    first = setup.client.cookies.get(COOKIE_NAME)
    login(setup)
    setup.client.post("/api/auth/logout")
    assert (
        setup.client.get(
            "/api/auth/me", headers={"Cookie": f"{COOKIE_NAME}={first}"}
        ).status_code
        == 200
    )


def test_database_expiry_enforced(setup):
    login(setup)
    token = setup.client.cookies.get(COOKIE_NAME)
    from sqlalchemy import select

    with setup.factory.begin() as db:
        session = db.scalar(
            select(SesionInterna).where(
                SesionInterna.token_hash == SessionRepository.token_hash(token)
            )
        )
        session.creada_en = datetime.now(timezone.utc) - timedelta(hours=2)
        session.expira_en = datetime.now(timezone.utc) - timedelta(hours=1)
    assert setup.client.get("/api/auth/me").status_code == 401


def test_inactive_user_with_existing_token(setup):
    login(setup)
    with setup.factory.begin() as db:
        db.get(UsuarioInterno, setup.ids["admin"]).activo = False
    assert setup.client.get("/api/auth/me").status_code == 401


def test_cors_and_origin(setup):
    headers = {"Origin": "https://untrusted.example"}
    assert (
        setup.client.post(
            "/api/auth/login",
            json={"email": setup.emails["admin"], "password": PASSWORD},
            headers=headers,
        ).status_code
        == 403
    )
    login(setup)
    assert setup.client.post("/api/auth/logout", headers=headers).status_code == 403
    assert setup.client.get("/api/auth/me").status_code == 200
    response = setup.client.options(
        "/api/users",
        headers={
            "Origin": "http://localhost:5173",
            "Access-Control-Request-Method": "PATCH",
        },
    )
    assert response.status_code == 200
    assert (
        setup.client.options(
            "/api/users", headers={**headers, "Access-Control-Request-Method": "PATCH"}
        ).status_code
        == 400
    )


def test_server_error_safe(setup, monkeypatch):
    def fail(email):
        raise RuntimeError("private details")

    monkeypatch.setattr(setup.app.state.users, "by_email", fail)
    response = login(setup)
    assert response.status_code == 500
    assert response.json() == {"detail": "No pudimos procesar la solicitud."}


def test_secure_cookie(setup):
    setup.settings.cookie_secure = True
    assert "Secure" in login(setup).headers["set-cookie"]


def test_failed_login_clears_session(setup):
    login(setup)
    login(setup, password="bad")
    assert setup.client.get("/api/auth/me").status_code == 401


def test_weak_key_rejected():
    with pytest.raises(ValueError):
        Settings(_env_file=None, jwt_secret_key="short")


def test_argon2(password_hash):
    assert password_hash.startswith("$argon2id$")
    assert password_hasher.verify(PASSWORD, password_hash)


@pytest.mark.parametrize("name", ["admin", "inactive"])
def test_rate_limit_and_release(setup, name):
    clock = [1000.0]
    setup.app.state.auth.clock = lambda: clock[0]
    for _ in range(7):
        assert login(setup, name, "bad").status_code == 401
    response = login(setup, name, "bad")
    assert response.status_code == 429 and response.headers["retry-after"] == "900"
    clock[0] += 900
    assert login(setup, name, "bad").status_code == 401


def test_success_does_not_consume_failure_quota(setup):
    for _ in range(9):
        assert login(setup).status_code == 200


def test_ip_limit_and_parallel_reservation():
    from concurrent.futures import ThreadPoolExecutor

    from app.auth.state import LoginLimited

    auth = AuthState()
    for i in range(40):
        auth.begin_login(f"user{i}", "same-ip")
    with pytest.raises(LoginLimited):
        auth.begin_login("other", "same-ip")
    auth = AuthState()

    def attempt(i):
        try:
            auth.begin_login("same-email", str(i))
            return True
        except LoginLimited:
            return False

    with ThreadPoolExecutor(max_workers=16) as pool:
        assert sum(pool.map(attempt, range(16))) == 8
