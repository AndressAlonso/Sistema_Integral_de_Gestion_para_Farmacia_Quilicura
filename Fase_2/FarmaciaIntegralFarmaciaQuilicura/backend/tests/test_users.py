"""E1-H2: aceptación, autorización y persistencia temporal reproducible."""

import json
from concurrent.futures import ThreadPoolExecutor

import pytest
from fastapi.testclient import TestClient

from app.auth.security import password_hasher
from app.auth.users import DuplicateEmail, LocalUserRepository
from app.config import Settings
from app.main import create_app

PASSWORD = "Solo-pruebas-E1H2!"


@pytest.fixture(scope="module")
def hashed_password():
    return password_hasher.hash(PASSWORD)


@pytest.fixture
def setup(tmp_path, hashed_password):
    path = tmp_path / "users.json"
    path.write_text(
        json.dumps(
            [
                {
                    "id": 1,
                    "name": "Admin",
                    "email": "admin@farmacia.cl",
                    "password_hash": hashed_password,
                    "is_active": True,
                    "roles": ["ADMINISTRADOR"],
                },
                {
                    "id": 2,
                    "name": "Cajero",
                    "email": "cajero@farmacia.cl",
                    "password_hash": hashed_password,
                    "is_active": True,
                    "roles": ["CAJERO"],
                },
                {
                    "id": 3,
                    "name": "Inactivo",
                    "email": "inactivo@farmacia.cl",
                    "password_hash": hashed_password,
                    "is_active": False,
                    "roles": ["CAJERO"],
                },
            ]
        ),
        encoding="utf-8",
    )
    settings = Settings(
        _env_file=None, jwt_secret_key="only-tests-" * 8, users_file=path
    )
    app = create_app(settings)
    with TestClient(app, raise_server_exceptions=False) as client:
        yield client, app, path


def login(client, email="admin@farmacia.cl", password=PASSWORD):
    return client.post("/api/auth/login", json={"email": email, "password": password})


def new_user(**overrides):
    return {
        "name": "Ana Torres",
        "email": "ana@farmacia.cl",
        "password": PASSWORD,
        "roles": ["CAJERO"],
        "is_active": True,
        **overrides,
    }


def test_create_persists_hashed_user_and_allows_real_login(setup):
    client, _, path = setup
    login(client)
    response = client.post("/api/users", json=new_user())
    assert response.status_code == 201
    assert response.json() == {
        "id": 4,
        "name": "Ana Torres",
        "email": "ana@farmacia.cl",
        "roles": ["CAJERO"],
        "is_active": True,
    }
    assert PASSWORD not in path.read_text(encoding="utf-8")
    user = LocalUserRepository(path).by_id(4)
    assert password_hasher.verify(PASSWORD, user.password_hash)
    assert login(client, "ana@farmacia.cl").status_code == 200
    assert client.get("/api/auth/me").json()["user"]["id"] == 4


def test_list_exposes_public_data_and_current_actor_only(setup):
    client, _, _ = setup
    login(client)
    response = client.get("/api/users")
    assert response.status_code == 200
    assert len(response.json()["users"]) == 3
    assert response.json()["current_user"]["roles"] == ["ADMINISTRADOR"]
    assert "password" not in response.text and "argon2" not in response.text


@pytest.mark.parametrize("email", ["admin@farmacia.cl", " ADMIN@FARMACIA.CL "])
def test_duplicate_email_returns_conflict_without_writing(setup, email):
    client, _, path = setup
    login(client)
    previous = path.read_bytes()
    response = client.post("/api/users", json=new_user(email=email))
    assert response.status_code == 409
    assert path.read_bytes() == previous


def test_update_persists_without_replacing_password_or_id(setup):
    client, _, path = setup
    login(client)
    original = LocalUserRepository(path).by_id(2)
    response = client.patch(
        "/api/users/2",
        json={
            "name": " Ana ",
            "email": " NUEVO@FARMACIA.CL ",
            "roles": ["CAJERO", "ADMINISTRADOR"],
        },
    )
    assert response.status_code == 200
    stored = LocalUserRepository(path).by_id(2)
    assert stored.name == "Ana" and stored.email == "nuevo@farmacia.cl"
    assert stored.id == original.id and stored.password_hash == original.password_hash
    assert login(client, "nuevo@farmacia.cl").status_code == 200
    assert client.get("/api/users").status_code == 200


def test_update_duplicate_email_rejected_and_own_email_allowed(setup):
    client, _, _ = setup
    login(client)
    assert (
        client.patch("/api/users/2", json={"email": "ADMIN@farmacia.cl"}).status_code
        == 409
    )
    assert (
        client.patch("/api/users/2", json={"email": "CAJERO@farmacia.cl"}).status_code
        == 200
    )


@pytest.mark.parametrize(
    "changes",
    [
        {"name": " "},
        {"email": "invalid"},
        {"password": "short"},
        {"roles": []},
        {"roles": ["ROOT"]},
        {"roles": ["CAJERO", "CAJERO"]},
        {"is_active": "true"},
        {"password_hash": "secret"},
        {"id": 99},
    ],
)
def test_invalid_create_is_rejected_without_echoing_input(setup, changes):
    client, _, path = setup
    login(client)
    before = path.read_bytes()
    response = client.post("/api/users", json=new_user(**changes))
    assert response.status_code == 422
    assert PASSWORD not in response.text and "password_hash" not in response.text
    assert path.read_bytes() == before


@pytest.mark.parametrize(
    "body",
    [
        {},
        {"name": None},
        {"roles": []},
        {"email": "bad"},
        {"is_active": True},
        {"password": PASSWORD},
    ],
)
def test_invalid_update_does_not_modify_data(setup, body):
    client, _, path = setup
    login(client)
    before = path.read_bytes()
    assert client.patch("/api/users/2", json=body).status_code == 422
    assert path.read_bytes() == before


@pytest.mark.parametrize(
    "method,path,body",
    [
        ("GET", "/api/users", None),
        ("POST", "/api/users", new_user()),
        ("PATCH", "/api/users/1", {"name": "Changed"}),
        ("POST", "/api/users/1/deactivate", None),
    ],
)
def test_anonymous_and_non_admin_cannot_access_directly(setup, method, path, body):
    client, _, _ = setup
    assert client.request(method, path, json=body).status_code == 401
    login(client, "cajero@farmacia.cl")
    assert client.request(method, path, json=body).status_code == 403


def test_deactivation_blocks_existing_session_and_login_preserves_record(setup):
    client, app, path = setup
    with TestClient(app) as staff:
        login(staff, "cajero@farmacia.cl")
        login(client)
        response = client.post("/api/users/2/deactivate")
        assert response.status_code == 200
        assert response.json()["is_active"] is False
        assert LocalUserRepository(path).by_id(2) is not None
        assert staff.get("/api/auth/me").status_code == 401
        assert login(staff, "cajero@farmacia.cl").status_code == 401
        assert client.post("/api/users/2/deactivate").status_code == 200


def test_new_inactive_user_cannot_login(setup):
    client, _, _ = setup
    login(client)
    assert client.post("/api/users", json=new_user(is_active=False)).status_code == 201
    assert login(client, "ana@farmacia.cl").status_code == 401


def test_permission_change_takes_effect_in_existing_session(setup):
    client, app, _ = setup
    with TestClient(app) as other:
        login(client)
        login(other)
        assert (
            client.patch("/api/users/1", json={"roles": ["CAJERO"]}).status_code == 200
        )
        assert other.get("/api/users").status_code == 403


@pytest.mark.parametrize(
    "method,path,body",
    [
        ("POST", "/api/users", new_user()),
        ("PATCH", "/api/users/2", {"name": "Changed"}),
        ("POST", "/api/users/2/deactivate", None),
    ],
)
def test_mutations_reject_untrusted_origin(setup, method, path, body):
    client, _, _ = setup
    login(client)
    assert (
        client.request(
            method, path, json=body, headers={"Origin": "https://untrusted.example"}
        ).status_code
        == 403
    )


def test_missing_user_returns_404(setup):
    client, _, _ = setup
    login(client)
    assert client.patch("/api/users/999", json={"name": "Ana"}).status_code == 404
    assert client.post("/api/users/999/deactivate").status_code == 404


def test_write_failure_keeps_original_file_and_returns_safe_error(setup, monkeypatch):
    client, _, path = setup
    login(client)
    before = path.read_bytes()

    def fail(*args):
        raise OSError("sensitive-path-secret")

    monkeypatch.setattr("app.auth.users.os.replace", fail)
    response = client.post("/api/users", json=new_user())
    assert response.status_code == 500
    assert "sensitive" not in response.text
    assert path.read_bytes() == before


def test_parallel_creates_cannot_duplicate_email_or_lose_distinct_users(
    setup, hashed_password
):
    _, app, path = setup
    repo = app.state.users

    def create(email):
        try:
            repo.create(
                name="Prueba",
                email=email,
                password_hash=hashed_password,
                is_active=True,
                roles=["CAJERO"],
            )
            return True
        except DuplicateEmail:
            return False

    with ThreadPoolExecutor(max_workers=8) as pool:
        assert sum(pool.map(create, ["new@farmacia.cl"] * 8)) == 1
        assert all(pool.map(create, [f"user{i}@farmacia.cl" for i in range(8)]))
    users = LocalUserRepository(path).list_users()
    assert len(users) == 12
    assert len({u.id for u in users}) == 12
