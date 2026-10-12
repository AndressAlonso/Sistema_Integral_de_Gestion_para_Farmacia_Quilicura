"""E6-H2: seguridad sin DDL; integración PostgreSQL con rollback tras autorizar 0012."""
from datetime import datetime, timedelta, timezone
from importlib.util import module_from_spec, spec_from_file_location
from io import StringIO
from pathlib import Path
from secrets import token_urlsafe
from uuid import uuid4

import jwt
import pytest
from alembic.migration import MigrationContext
from alembic.operations import Operations
from app.auth.security import (
    create_token,
    password_hasher,
    validate_token,
    verify_password,
)
from app.auth.state import AuthState, LoginLimited
from app.config import Settings
from app.customers.models import Cliente, SesionCliente
from app.customers.schemas import LoginRequest, RegisterRequest
from app.customers.security import (
    COOKIE_NAME,
    clear_customer_cookie,
    cookie_options,
    create_customer_token,
    validate_customer_token,
)
from app.main import create_app
from fastapi.testclient import TestClient
from jwt import InvalidTokenError
from pydantic import ValidationError
from sqlalchemy import inspect, select


@pytest.fixture
def settings():
    return Settings(_env_file=None, jwt_secret_key=token_urlsafe(48))


def test_normalization_and_secret_redaction():
    secret = token_urlsafe(24)
    data = RegisterRequest(name=" Cliente ", email=" CLIENTE@EXAMPLE.COM ", password=secret)
    assert data.name == "Cliente" and data.email == "cliente@example.com"
    assert secret not in repr(data) and secret not in data.model_dump_json()
    hashed = password_hasher.hash(data.password.get_secret_value())
    assert hashed.startswith("$argon2id$") and verify_password(secret, hashed)
    assert not verify_password(token_urlsafe(24), hashed)


@pytest.mark.parametrize("length", [0, 11, 129])
def test_password_limits(length):
    with pytest.raises(ValidationError):
        LoginRequest(email="cliente@example.com", password=token_urlsafe(150)[:length])


@pytest.mark.parametrize("length", [12, 128])
def test_password_boundaries(length):
    assert len(LoginRequest(email="cliente@example.com", password=token_urlsafe(150)[:length]).password.get_secret_value()) == length


@pytest.mark.parametrize("changes", [{"name": "   "}, {"email": "invalid"}, {"confirmation": "extra"}, {"roles": []}])
def test_invalid_registration(changes):
    with pytest.raises(ValidationError):
        RegisterRequest(**({"name": "Cliente", "email": "cliente@example.com", "password": token_urlsafe(24)} | changes))


def test_token_audiences_are_isolated(settings):
    customer_token, _ = create_customer_token(uuid4(), settings)
    internal_token, _ = create_token(uuid4(), settings)
    assert validate_customer_token(customer_token, settings)["aud"] == "sigfq-customers"
    with pytest.raises(InvalidTokenError):
        validate_token(customer_token, settings)
    with pytest.raises(InvalidTokenError):
        validate_customer_token(internal_token, settings)


@pytest.mark.parametrize("variant", ["expired", "missing_exp", "signature", "issuer"])
def test_invalid_customer_claims(settings, variant):
    token, _ = create_customer_token(uuid4(), settings)
    claims = validate_customer_token(token, settings)
    key = settings.jwt_secret_key.get_secret_value()
    if variant == "expired":
        claims["exp"] = int((datetime.now(timezone.utc) - timedelta(seconds=1)).timestamp())
    elif variant == "missing_exp":
        del claims["exp"]
    elif variant == "signature":
        key = token_urlsafe(48)
    else:
        claims["iss"] = "other"
    with pytest.raises(InvalidTokenError):
        validate_customer_token(jwt.encode(claims, key, algorithm="HS256"), settings)


@pytest.mark.parametrize("secure", [False, True])
def test_cookie_creation_and_deletion_match(settings, secure):
    from fastapi import Response
    settings.cookie_secure = secure
    created, deleted = Response(), Response()
    created.set_cookie(COOKIE_NAME, "test-token", **cookie_options(settings))
    clear_customer_cookie(deleted, settings)
    for response in (created, deleted):
        header = response.headers["set-cookie"]
        assert "Path=/api/customers" in header and "SameSite=strict" in header and "HttpOnly" in header
        assert ("Secure" in header) == secure
    assert "Max-Age=0" in deleted.headers["set-cookie"]


def test_http_errors_cookie_isolation_without_database(settings):
    # No lifespan: these requests fail validation/token decoding before repositories are accessed.
    client = TestClient(create_app(settings))
    customer = client.get("/api/customers/me", headers={"Cookie": "sigfq_session=internal"})
    assert customer.status_code == 401
    assert "sigfq_customer_session=" in customer.headers["set-cookie"]
    assert "sigfq_session=" not in customer.headers["set-cookie"]
    internal = client.get("/api/auth/me", headers={"Cookie": "sigfq_customer_session=customer"})
    assert internal.status_code == 401
    assert "sigfq_customer_session=" not in internal.headers["set-cookie"]
    assert "sigfq_session=" in internal.headers["set-cookie"]
    secret = token_urlsafe(6)
    invalid = client.post("/api/customers/register", json={"name": "Cliente", "email": "invalid", "password": secret})
    assert invalid.status_code == 422 and secret not in invalid.text
    assert client.post("/api/customers/logout").status_code == 204
    assert client.post("/api/customers/register", headers={"Origin": "https://untrusted.example"},
                       json={"name": "Cliente", "email": "cliente@example.com", "password": token_urlsafe(24)}).status_code == 403


def test_rate_limiter_instances_are_independent():
    customers, internal = AuthState(), AuthState()
    for _ in range(8):
        customers.begin_login("cliente@example.com", "same-ip")
    with pytest.raises(LoginLimited):
        customers.begin_login("cliente@example.com", "same-ip")
    assert internal.begin_login("cliente@example.com", "same-ip")


def test_migration_sql_without_database():
    path = Path(__file__).parents[1] / "migrations/versions/0012_clientes.py"
    spec = spec_from_file_location("customer_migration", path)
    module = module_from_spec(spec)
    spec.loader.exec_module(module)
    assert module.down_revision == "0011_evento_auditoria"
    output = StringIO()
    module.op = Operations(MigrationContext.configure(dialect_name="postgresql", opts={"as_sql": True, "output_buffer": output}))
    module.upgrade()
    sql = output.getvalue()
    assert "CREATE TABLE cliente" in sql and "CREATE TABLE sesion_cliente" in sql
    assert "UNIQUE (token_hash)" in sql and "UNIQUE (cliente_id)" not in sql
    assert "CREATE INDEX ix_sesion_cliente_cliente_id" in sql
    output.seek(0)
    output.truncate()
    module.downgrade()
    sql = output.getvalue()
    assert sql.index("DROP TABLE sesion_cliente") < sql.index("DROP TABLE cliente")


@pytest.fixture
def customer_setup(setup):
    with setup.factory() as db:
        if not {"cliente", "sesion_cliente"}.issubset(inspect(db.connection()).get_table_names()):
            pytest.skip("Pendiente: autorización y aplicación de 0012_clientes")
    return setup


def test_customer_persistence_and_multiple_sessions(customer_setup):
    ctx = customer_setup
    secret = token_urlsafe(24)
    email = ctx.emails["admin"]  # Same email as internal identity is allowed.
    body = {"name": "Cliente temporal", "email": f" {email.upper()} ", "password": secret}
    response = ctx.client.post("/api/customers/register", json=body)
    assert response.status_code == 201 and response.json()["email"] == email
    assert set(response.json()) == {"id", "name", "email"}
    assert COOKIE_NAME not in ctx.client.cookies
    assert ctx.client.post("/api/customers/register", json=body).status_code == 409
    credentials = {"email": email, "password": secret}
    assert ctx.client.post("/api/customers/login", json=credentials).status_code == 200
    first = ctx.client.cookies.get(COOKIE_NAME)
    assert ctx.client.post("/api/customers/login", json=credentials).status_code == 200
    second = ctx.client.cookies.get(COOKIE_NAME)
    assert first != second
    with ctx.factory() as db:
        customer = db.scalar(select(Cliente).where(Cliente.correo == email))
        assert customer.password_hash.startswith("$argon2id$")
        assert len(list(db.scalars(select(SesionCliente).where(SesionCliente.cliente_id == customer.id)))) == 2
    assert ctx.client.get("/api/customers/me").status_code == 200
    assert ctx.client.post("/api/customers/logout").status_code == 204
    assert ctx.client.get("/api/customers/me", headers={"Cookie": f"{COOKIE_NAME}={second}"}).status_code == 401
    assert ctx.client.get("/api/customers/me", headers={"Cookie": f"{COOKIE_NAME}={first}"}).status_code == 200


def test_live_identity_isolation_and_generic_failures(customer_setup):
    from conftest import PASSWORD
    ctx = customer_setup
    assert ctx.client.post("/api/auth/login", json={"email": ctx.emails["admin"], "password": PASSWORD}).status_code == 200
    internal = ctx.client.cookies.get("sigfq_session")
    secret = token_urlsafe(24)
    email = f"customer-{ctx.suffix}@example.com"
    ctx.client.post("/api/customers/register", json={"name": "Cliente", "email": email, "password": secret})
    invalid = {"email": email, "password": token_urlsafe(24)}
    assert ctx.client.post("/api/customers/login", json=invalid).json() == {"detail": "Correo o contraseña incorrectos."}
    assert ctx.client.cookies.get("sigfq_session") == internal
    assert ctx.client.get("/api/auth/me").status_code == 200
    assert ctx.client.post("/api/customers/login", json={"email": email, "password": secret}).status_code == 200
    customer_token = ctx.client.cookies.get(COOKIE_NAME)
    ctx.client.post("/api/auth/login", json={"email": ctx.emails["admin"], "password": token_urlsafe(24)})
    assert ctx.client.cookies.get(COOKIE_NAME) == customer_token
    assert ctx.client.get("/api/customers/me").status_code == 200
    with ctx.factory.begin() as db:
        db.scalar(select(Cliente).where(Cliente.correo == email)).activo = False
    assert ctx.client.get("/api/customers/me").status_code == 401
    assert ctx.client.post("/api/customers/login", json={"email": email, "password": secret}).json() == {"detail": "Correo o contraseña incorrectos."}


def test_customer_logout_preserves_active_internal_session(customer_setup):
    from conftest import PASSWORD

    ctx = customer_setup
    assert ctx.client.post("/api/auth/login", json={"email": ctx.emails["admin"], "password": PASSWORD}).status_code == 200
    internal = ctx.client.cookies.get("sigfq_session")
    secret = token_urlsafe(24)
    email = f"logout-{ctx.suffix}@example.com"
    assert ctx.client.post("/api/customers/register", json={"name": "Cliente temporal", "email": email, "password": secret}).status_code == 201
    assert ctx.client.post("/api/customers/login", json={"email": email, "password": secret}).status_code == 200
    assert ctx.client.get("/api/customers/me").json()["customer"]["name"] == "Cliente temporal"
    response = ctx.client.post("/api/customers/logout")
    assert response.status_code == 204
    assert "sigfq_session=" not in response.headers["set-cookie"]
    assert COOKIE_NAME not in ctx.client.cookies
    assert ctx.client.cookies.get("sigfq_session") == internal
    assert ctx.client.get("/api/customers/me").status_code == 401
    assert ctx.client.cookies.get("sigfq_session") == internal
    assert ctx.client.get("/api/auth/me").status_code == 200
