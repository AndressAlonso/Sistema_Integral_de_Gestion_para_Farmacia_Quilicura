import json
from datetime import datetime, timedelta, timezone

import jwt
import pytest
from fastapi.testclient import TestClient

from app.auth.routes import COOKIE_NAME
from app.auth.security import password_hasher
from app.config import Settings
from app.main import create_app

PASSWORD = "Solo-pruebas-E1H1!"


@pytest.fixture(scope="session")
def password_hash():
    return password_hasher.hash(PASSWORD)


@pytest.fixture
def setup(tmp_path, password_hash):
    path = tmp_path / "users.json"
    path.write_text(
        json.dumps(
            [
                {
                    "id": 1,
                    "email": "interno@farmacia.cl",
                    "password_hash": password_hash,
                    "is_active": True,
                },
                {
                    "id": 2,
                    "email": "inactivo@farmacia.cl",
                    "password_hash": password_hash,
                    "is_active": False,
                },
            ]
        ),
        encoding="utf-8",
    )
    settings = Settings(
        _env_file=None, jwt_secret_key="test-only-" * 8, users_file=path
    )
    app = create_app(settings)
    with TestClient(app, raise_server_exceptions=False) as client:
        yield client, settings, app


def login(client, email="interno@farmacia.cl", password=PASSWORD):
    return client.post("/api/auth/login", json={"email": email, "password": password})


def test_valid_login_exposes_only_public_user_and_secure_cookie(setup):
    client, settings, _ = setup
    response = login(client)
    assert response.status_code == 200
    assert set(response.json()) == {"user", "expires_at"}
    assert response.json()["user"] == {"id": 1, "email": "interno@farmacia.cl"}
    assert PASSWORD not in response.text
    cookie = response.headers["set-cookie"]
    assert (
        "HttpOnly" in cookie
        and "SameSite=strict" in cookie
        and "Path=/api/auth" in cookie
    )
    assert f"Max-Age={settings.access_token_expire_minutes * 60}" in cookie
    assert response.headers["cache-control"] == "no-store"


@pytest.mark.parametrize(
    "email,password",
    [
        ("interno@farmacia.cl", "incorrecta"),
        ("desconocido@farmacia.cl", PASSWORD),
        ("inactivo@farmacia.cl", PASSWORD),
        ("inactivo@farmacia.cl", "incorrecta"),
    ],
)
def test_rejected_login_is_indistinguishable(setup, email, password):
    client, _, _ = setup
    response = login(client, email, password)
    assert response.status_code == 401
    assert response.json() == {"detail": "Correo o contraseña incorrectos."}
    assert not client.cookies.get(COOKIE_NAME)


def test_email_is_trimmed_and_case_insensitive(setup):
    assert login(setup[0], " INTERNO@FARMACIA.CL ").status_code == 200


def test_valid_cookie_restores_session(setup):
    client, _, _ = setup
    login(client)
    response = client.get("/api/auth/me")
    assert response.status_code == 200
    assert response.json()["user"]["id"] == 1
    assert "password_hash" not in response.text


@pytest.mark.parametrize(
    "token", [None, "invalid", "eyJhbGciOiJub25lIn0.eyJzdWIiOiIxIn0."]
)
def test_missing_or_invalid_token(setup, token):
    client, _, _ = setup
    headers = {"Cookie": f"{COOKIE_NAME}={token}"} if token else {}
    response = client.get("/api/auth/me", headers=headers)
    assert response.status_code == 401
    assert "Max-Age=0" in response.headers["set-cookie"]


@pytest.mark.parametrize(
    "variant",
    [
        "expired",
        "wrong_signature",
        "missing_exp",
        "wrong_audience",
        "unknown_user",
        "bad_subject",
        "wrong_algorithm",
    ],
)
def test_token_validation_rejects_invalid_claims(setup, variant):
    client, settings, app = setup
    now = datetime.now(timezone.utc)
    claims = {
        "sub": "1",
        "jti": "test-session",
        "iat": now,
        "exp": now + timedelta(minutes=5),
        "iss": "sigfq",
        "aud": "sigfq-internal",
    }
    key = settings.jwt_secret_key.get_secret_value()
    algorithm = "HS256"
    if variant == "expired":
        claims["exp"] = now - timedelta(seconds=1)
    elif variant == "wrong_signature":
        key = "another-test-key-" * 4
    elif variant == "missing_exp":
        del claims["exp"]
    elif variant == "wrong_audience":
        claims["aud"] = "other"
    elif variant == "unknown_user":
        claims["sub"] = "999"
    elif variant == "bad_subject":
        claims["sub"] = "not-an-id"
    elif variant == "wrong_algorithm":
        algorithm = "HS384"
    token = jwt.encode(claims, key, algorithm=algorithm)
    app.state.auth.register_session(
        "test-session", (now + timedelta(minutes=5)).timestamp()
    )
    assert (
        client.get(
            "/api/auth/me", headers={"Cookie": f"{COOKIE_NAME}={token}"}
        ).status_code
        == 401
    )


def test_deactivated_user_cannot_reuse_session(setup):
    client, settings, _ = setup
    login(client)
    users = json.loads(settings.users_file.read_text(encoding="utf-8"))
    users[0]["is_active"] = False
    settings.users_file.write_text(json.dumps(users), encoding="utf-8")
    assert client.get("/api/auth/me").status_code == 401
    assert not client.cookies.get(COOKIE_NAME)


@pytest.mark.parametrize(
    "body",
    [
        {},
        {"email": "not-email", "password": PASSWORD},
        {"email": "interno@farmacia.cl", "password": ""},
        {"email": "interno@farmacia.cl", "password": "x" * 1025},
    ],
)
def test_validation_does_not_echo_credentials(setup, body):
    response = setup[0].post("/api/auth/login", json=body)
    assert response.status_code == 422
    assert response.json() == {"detail": "Revisa el correo y la contraseña ingresados."}


def test_malformed_json_is_controlled(setup):
    response = setup[0].post(
        "/api/auth/login", content="{", headers={"Content-Type": "application/json"}
    )
    assert response.status_code == 422
    assert "input" not in response.text


def test_failed_login_clears_previous_session(setup):
    client, _, _ = setup
    login(client)
    login(client, password="incorrecta")
    assert client.get("/api/auth/me").status_code == 401


def test_unexpected_error_is_generic(setup, monkeypatch):
    client, _, app = setup

    def broken_lookup(email):
        raise RuntimeError("sensitive internals")

    monkeypatch.setattr(app.state.users, "by_email", broken_lookup)
    response = login(client)
    assert response.status_code == 500
    assert response.json() == {"detail": "No pudimos procesar la solicitud."}


def test_cors_and_login_origin(setup):
    client, _, _ = setup
    response = client.post(
        "/api/auth/login",
        json={"email": "interno@farmacia.cl", "password": PASSWORD},
        headers={"Origin": "https://untrusted.example"},
    )
    assert response.status_code == 403
    assert "access-control-allow-origin" not in response.headers
    response = client.options(
        "/api/auth/login",
        headers={
            "Origin": "http://localhost:5173",
            "Access-Control-Request-Method": "POST",
        },
    )
    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == "http://localhost:5173"
    response = client.options(
        "/api/auth/login",
        headers={
            "Origin": "https://untrusted.example",
            "Access-Control-Request-Method": "POST",
        },
    )
    assert response.status_code == 400


def test_secure_cookie_configuration(setup):
    client, settings, _ = setup
    settings.cookie_secure = True
    assert "Secure" in login(client).headers["set-cookie"]


def test_weak_secret_is_rejected():
    with pytest.raises(ValueError):
        Settings(_env_file=None, jwt_secret_key="short")


def test_passwords_are_argon2_hashes(password_hash):
    assert password_hash.startswith("$argon2id$")
    assert PASSWORD not in password_hash
    assert password_hasher.verify(PASSWORD, password_hash)


@pytest.mark.parametrize(
    "email", ["interno@farmacia.cl", "inactivo@farmacia.cl", "nadie@farmacia.cl"]
)
def test_eighth_failure_limits_email_and_releases_after_window(setup, email):
    client, _, app = setup
    clock = [1000.0]
    app.state.auth.clock = lambda: clock[0]
    for _ in range(7):
        assert login(client, email, "incorrecta").status_code == 401
    response = login(client, email.upper(), "incorrecta")
    assert response.status_code == 429
    assert response.headers["retry-after"] == "900"
    assert login(client, email).status_code == 429
    clock[0] += 60
    assert login(client, email).headers["retry-after"] == "840"
    clock[0] += 840
    assert login(client, email, "incorrecta").status_code == 401


def test_success_does_not_count_as_email_failure(setup):
    client, _, _ = setup
    for _ in range(9):
        assert login(client).status_code == 200


def test_ip_limit_cannot_be_bypassed_by_changing_email(setup):
    client, _, _ = setup
    for index in range(39):
        assert (
            login(client, f"user{index}@farmacia.cl", "incorrecta").status_code == 401
        )
    assert login(client, "user40@farmacia.cl", "incorrecta").status_code == 429
    assert login(client).status_code == 429


def test_limit_reserves_parallel_attempts_atomically():
    from concurrent.futures import ThreadPoolExecutor

    from app.auth.state import AuthState, LoginLimited

    auth = AuthState()

    def attempt(index):
        try:
            auth.begin_login("interno@farmacia.cl", str(index))
            return True
        except LoginLimited:
            return False

    with ThreadPoolExecutor(max_workers=16) as pool:
        assert sum(pool.map(attempt, range(16))) == 8


def test_logout_revokes_copied_token_and_is_idempotent(setup):
    client, _, _ = setup
    login(client)
    copied = client.cookies.get(COOKIE_NAME)
    response = client.post(
        "/api/auth/logout", headers={"Origin": "http://localhost:5173"}
    )
    assert response.status_code == 204
    assert not client.cookies.get(COOKIE_NAME)
    assert (
        client.get(
            "/api/auth/me", headers={"Cookie": f"{COOKIE_NAME}={copied}"}
        ).status_code
        == 401
    )
    assert client.post("/api/auth/logout").status_code == 204
    assert login(client).status_code == 200
    assert client.get("/api/auth/me").status_code == 200


def test_logout_only_revokes_current_session(setup):
    client, _, _ = setup
    login(client)
    first_token = client.cookies.get(COOKIE_NAME)
    login(client)
    second_token = client.cookies.get(COOKIE_NAME)
    assert first_token != second_token
    client.post("/api/auth/logout")
    assert (
        client.get(
            "/api/auth/me", headers={"Cookie": f"{COOKIE_NAME}={first_token}"}
        ).status_code
        == 200
    )


def test_logout_rejects_untrusted_origin(setup):
    client, _, _ = setup
    login(client)
    assert (
        client.post(
            "/api/auth/logout", headers={"Origin": "https://untrusted.example"}
        ).status_code
        == 403
    )
    assert client.get("/api/auth/me").status_code == 200


def test_restart_does_not_restore_revoked_sessions(setup):
    from app.auth.state import AuthState

    client, _, app = setup
    login(client)
    copied = client.cookies.get(COOKIE_NAME)
    client.post("/api/auth/logout")
    app.state.auth = AuthState()
    assert (
        client.get(
            "/api/auth/me", headers={"Cookie": f"{COOKIE_NAME}={copied}"}
        ).status_code
        == 401
    )
