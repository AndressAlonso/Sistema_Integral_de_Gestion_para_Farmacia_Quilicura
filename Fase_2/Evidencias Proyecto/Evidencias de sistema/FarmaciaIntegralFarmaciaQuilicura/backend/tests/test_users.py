from uuid import uuid4

import pytest
from conftest import PASSWORD
from sqlalchemy import func, select
from test_auth import login

from app.auth.security import password_hasher
from app.auth.users import DuplicateEmail
from app.models import SesionInterna, Sucursal, UsuarioInterno


def payload(ctx, **changes):
    return {
        "name": "Ana de prueba",
        "email": f"new-{ctx.suffix}@farmacia.cl",
        "password": PASSWORD,
        "is_active": True,
        "role_ids": [str(ctx.ids["operator_role"])],
        "branch_id": str(ctx.ids["branch"]),
        **changes,
    }


def test_create_user_persist_and_login(setup):
    login(setup)
    response = setup.client.post("/api/users", json=payload(setup))
    assert response.status_code == 201
    user = response.json()
    assert user["branch_id"] == str(setup.ids["branch"])
    assert "password" not in response.text
    with setup.factory() as db:
        row = db.scalar(
            select(UsuarioInterno).where(UsuarioInterno.correo == user["email"])
        )
        assert password_hasher.verify(PASSWORD, row.password_hash)
        assert len(row.roles) == 1
    assert (
        setup.client.post(
            "/api/auth/login", json={"email": user["email"], "password": PASSWORD}
        ).status_code
        == 200
    )


def test_list_real_options_and_safe_fields(setup):
    login(setup)
    response = setup.client.get("/api/users")
    assert response.status_code == 200
    data = response.json()
    assert str(setup.ids["admin"]) in {u["id"] for u in data["users"]}
    assert str(setup.ids["branch"]) in {b["id"] for b in data["branches"]}
    assert str(setup.ids["admin_role"]) in {r["id"] for r in data["roles"]}
    assert "password" not in response.text


def test_duplicate_create_and_update(setup):
    login(setup)
    assert (
        setup.client.post(
            "/api/users",
            json=payload(setup, email=f" {setup.emails['admin'].upper()} "),
        ).status_code
        == 409
    )
    target = str(setup.ids["operator"])
    assert (
        setup.client.patch(
            f"/api/users/{target}", json={"email": setup.emails["admin"]}
        ).status_code
        == 409
    )
    assert (
        setup.client.patch(
            f"/api/users/{target}", json={"email": setup.emails["operator"].upper()}
        ).status_code
        == 200
    )


def test_update_preserves_hash_id_and_branch(setup):
    login(setup)
    target = setup.ids["operator"]
    before = setup.app.state.users.by_id(target)
    response = setup.client.patch(
        f"/api/users/{target}",
        json={"name": " Nuevo nombre ", "email": f"changed-{setup.suffix}@farmacia.cl"},
    )
    assert response.status_code == 200
    after = setup.app.state.users.by_id(target)
    assert after.name == "Nuevo nombre"
    assert (
        after.password_hash == before.password_hash
        and after.branch_id == before.branch_id
    )


@pytest.mark.parametrize(
    "field,value",
    [
        ("name", " "),
        ("email", "bad"),
        ("password", "short"),
        ("role_ids", []),
        ("role_ids", ["bad-uuid"]),
        ("branch_id", "bad-uuid"),
        ("is_active", "true"),
        ("password_hash", "secret"),
        ("id", str(uuid4())),
    ],
)
def test_invalid_create(setup, field, value):
    login(setup)
    response = setup.client.post("/api/users", json=payload(setup, **{field: value}))
    assert response.status_code == 422
    assert PASSWORD not in response.text and "password_hash" not in response.text


@pytest.mark.parametrize(
    "field", ["name", "email", "password", "role_ids", "branch_id", "is_active"]
)
def test_required_fields(setup, field):
    login(setup)
    body = payload(setup)
    del body[field]
    assert setup.client.post("/api/users", json=body).status_code == 422


@pytest.mark.parametrize("field", ["role_ids", "branch_id"])
def test_unknown_reference_rolls_back(setup, field):
    login(setup)
    value = [str(uuid4())] if field == "role_ids" else str(uuid4())
    assert (
        setup.client.post(
            "/api/users", json=payload(setup, **{field: value})
        ).status_code
        == 422
    )
    assert setup.app.state.users.by_email(payload(setup)["email"]) is None


def test_duplicate_roles_rejected(setup):
    login(setup)
    role = str(setup.ids["operator_role"])
    assert (
        setup.client.post(
            "/api/users", json=payload(setup, role_ids=[role, role])
        ).status_code
        == 422
    )


@pytest.mark.parametrize(
    "body",
    [
        {},
        {"name": None},
        {"role_ids": []},
        {"is_active": True},
        {"password": PASSWORD},
        {"branch_id": str(uuid4())},
    ],
)
def test_patch_rejects_invalid_or_out_of_scope_fields(setup, body):
    login(setup)
    assert (
        setup.client.patch(f"/api/users/{setup.ids['operator']}", json=body).status_code
        == 422
    )


@pytest.mark.parametrize(
    "method,path",
    [("GET", ""), ("POST", ""), ("PATCH", "/target"), ("POST", "/target/deactivate")],
)
def test_anonymous_and_operator_denied(setup, method, path):
    url = "/api/users" + path.replace("target", str(setup.ids["operator"]))
    body = (
        payload(setup)
        if method == "POST" and not path
        else {"name": "Changed"}
        if method == "PATCH"
        else None
    )
    assert setup.client.request(method, url, json=body).status_code == 401
    login(setup, "operator")
    assert setup.client.request(method, url, json=body).status_code == 403


def test_cannot_deactivate_self_and_session_remains_valid(setup):
    login(setup)
    response = setup.client.post(f"/api/users/{setup.ids['admin']}/deactivate")
    assert response.status_code == 409
    assert response.json()['detail'] == 'No puedes desactivar tu propia cuenta.'
    assert setup.app.state.users.by_id(setup.ids['admin']).is_active
    assert setup.client.get('/api/auth/me').status_code == 200


def test_deactivation_revokes_sessions_and_blocks_login(setup):
    login(setup, "operator")
    copied = setup.client.cookies.get("sigfq_session")
    login(setup)
    target = setup.ids["operator"]
    assert setup.client.post(f"/api/users/{target}/deactivate").status_code == 200
    assert not setup.app.state.users.by_id(target).is_active
    assert (
        setup.client.get(
            "/api/auth/me", headers={"Cookie": f"sigfq_session={copied}"}
        ).status_code
        == 401
    )
    assert login(setup, "operator").status_code == 401
    login(setup)
    assert setup.client.post(f"/api/users/{target}/deactivate").status_code == 200
    with setup.factory() as db:
        assert (
            db.scalar(
                select(func.count())
                .select_from(SesionInterna)
                .where(
                    SesionInterna.usuario_id == target,
                    SesionInterna.revocada_en.is_(None),
                )
            )
            == 0
        )


def test_inactive_created_account(setup):
    login(setup)
    assert (
        setup.client.post(
            "/api/users", json=payload(setup, is_active=False)
        ).status_code
        == 201
    )
    assert (
        setup.client.post(
            "/api/auth/login",
            json={"email": payload(setup)["email"], "password": PASSWORD},
        ).status_code
        == 401
    )


def test_role_change_updates_permission_in_existing_session(setup):
    login(setup)
    assert (
        setup.client.patch(
            f"/api/users/{setup.ids['admin']}",
            json={"role_ids": [str(setup.ids["operator_role"])]},
        ).status_code
        == 200
    )
    assert setup.client.get("/api/users").status_code == 403


def test_manager_cannot_grant_roles_but_can_edit_name(setup):
    login(setup, "manager")
    assert setup.client.get("/api/users").status_code == 200
    assert setup.client.post("/api/users", json=payload(setup)).status_code == 403
    target = setup.ids["operator"]
    assert (
        setup.client.patch(
            f"/api/users/{target}", json={"role_ids": [str(setup.ids["admin_role"])]}
        ).status_code
        == 403
    )
    assert (
        setup.client.patch(
            f"/api/users/{target}",
            json={"name": "Editado", "role_ids": [str(setup.ids["operator_role"])]},
        ).status_code
        == 200
    )


@pytest.mark.parametrize(
    "method,path", [("POST", ""), ("PATCH", "/target"), ("POST", "/target/deactivate")]
)
def test_untrusted_origin(setup, method, path):
    login(setup)
    url = "/api/users" + path.replace("target", str(setup.ids["operator"]))
    body = (
        payload(setup)
        if not path
        else {"name": "Changed"}
        if method == "PATCH"
        else None
    )
    assert (
        setup.client.request(
            method, url, json=body, headers={"Origin": "https://untrusted.example"}
        ).status_code
        == 403
    )


def test_missing_user(setup):
    login(setup)
    target = uuid4()
    assert (
        setup.client.patch(f"/api/users/{target}", json={"name": "Test"}).status_code
        == 404
    )
    assert setup.client.post(f"/api/users/{target}/deactivate").status_code == 404


def test_database_unique_constraint_is_translated(setup, password_hash):
    repo = setup.app.state.users
    with pytest.raises(DuplicateEmail):
        repo.create(
            name="Duplicado",
            email=setup.emails["admin"],
            password_hash=password_hash,
            is_active=True,
            role_ids=[setup.ids["operator_role"]],
            branch_id=setup.ids["branch"],
        )
    assert repo.by_email(setup.emails["admin"]).id == setup.ids["admin"]


def test_transaction_failure_does_not_persist_partial_user(setup, monkeypatch):
    login(setup)
    repo = setup.app.state.users

    def fail(row):
        raise RuntimeError("private database details")

    monkeypatch.setattr(repo, "_to_user", fail)
    # La autenticación usa _to_user, por eso se ejerce el repositorio directamente.
    with pytest.raises(RuntimeError):
        repo.create(
            name="Atomicidad",
            email=payload(setup)["email"],
            password_hash=r"\$argon2id\$fixture",
            is_active=True,
            role_ids=[setup.ids["operator_role"]],
            branch_id=setup.ids["branch"],
        )
    with setup.factory() as db:
        assert (
            db.scalar(
                select(UsuarioInterno).where(
                    UsuarioInterno.correo == payload(setup)["email"]
                )
            )
            is None
        )
def test_create_user_rejects_inactive_branch(setup):
    inactive_branch_id = uuid4()

    with setup.factory.begin() as db:
        db.add(
            Sucursal(
                id=inactive_branch_id,
                codigo=f"INACTIVE-{setup.suffix[:8]}",
                nombre="Sucursal inactiva temporal",
                direccion_local="Direccion temporal",
                activa=False,
            )
        )

    login(setup)

    response = setup.client.post(
        "/api/users",
        json=payload(
            setup,
            branch_id=str(inactive_branch_id),
        ),
    )

    assert response.status_code == 422
    assert (
        setup.app.state.users.by_email(
            payload(setup)["email"]
        )
        is None
    )


def test_update_user_changes_active_branch(setup):
    second_branch_id = uuid4()

    with setup.factory.begin() as db:
        db.add(
            Sucursal(
                id=second_branch_id,
                codigo=f"ACTIVE-{setup.suffix[:8]}",
                nombre="Segunda sucursal activa",
                direccion_local="Direccion temporal",
                activa=True,
            )
        )

    login(setup)

    target = setup.ids["operator"]
    before = setup.app.state.users.by_id(target)

    response = setup.client.patch(
        f"/api/users/{target}",
        json={
            "branch_id": str(second_branch_id),
        },
    )

    assert response.status_code == 200

    user = response.json()

    assert user["branch_id"] == str(second_branch_id)
    assert user["branch_name"] == "Segunda sucursal activa"

    persisted = setup.app.state.users.by_id(target)

    assert before is not None
    assert persisted is not None
    assert persisted.id == before.id
    assert persisted.password_hash == before.password_hash
    assert persisted.role_ids == before.role_ids
    assert persisted.branch_id == second_branch_id
    assert persisted.branch_name == "Segunda sucursal activa"


def test_update_user_rejects_inactive_branch(setup):
    inactive_branch_id = uuid4()

    with setup.factory.begin() as db:
        db.add(
            Sucursal(
                id=inactive_branch_id,
                codigo=f"DISABLED-{setup.suffix[:8]}",
                nombre="Sucursal inactiva temporal",
                direccion_local="Direccion temporal",
                activa=False,
            )
        )

    login(setup)

    target = setup.ids["operator"]
    before = setup.app.state.users.by_id(target)

    response = setup.client.patch(
        f"/api/users/{target}",
        json={
            "branch_id": str(inactive_branch_id),
        },
    )

    assert response.status_code == 422

    after = setup.app.state.users.by_id(target)

    assert before is not None
    assert after is not None
    assert after.branch_id == before.branch_id
    assert after.branch_name == before.branch_name


def test_update_user_rejects_unknown_branch(setup):
    login(setup)

    target = setup.ids["operator"]
    before = setup.app.state.users.by_id(target)

    response = setup.client.patch(
        f"/api/users/{target}",
        json={
            "branch_id": str(uuid4()),
        },
    )

    assert response.status_code == 422

    after = setup.app.state.users.by_id(target)

    assert before is not None
    assert after is not None
    assert after.branch_id == before.branch_id


def test_user_options_include_branch_status(setup):
    login(setup)

    response = setup.client.get("/api/users")

    assert response.status_code == 200

    branches = response.json()["branches"]
    test_branch = next(
        branch
        for branch in branches
        if branch["id"] == str(setup.ids["branch"])
    )

    assert test_branch["name"] == "Sucursal de prueba temporal"
    assert test_branch["is_active"] is True
