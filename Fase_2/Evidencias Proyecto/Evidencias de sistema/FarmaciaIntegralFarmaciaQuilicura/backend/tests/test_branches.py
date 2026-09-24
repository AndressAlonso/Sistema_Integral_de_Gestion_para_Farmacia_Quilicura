from uuid import UUID, uuid4

import pytest
from sqlalchemy import select
from test_auth import login

from app.models import Sucursal, UsuarioInterno


def branch_payload(setup, **changes):
    return {
        "code": f"BR-{setup.suffix[:12]}",
        "name": "Sucursal automatizada",
        "address": "Direccion temporal de prueba",
        "is_active": True,
        **changes,
    }


def test_list_branches_returns_database_data(setup):
    login(setup)

    response = setup.client.get("/api/branches")

    assert response.status_code == 200

    data = response.json()

    assert "branches" in data
    assert str(setup.ids["branch"]) in {
        branch["id"]
        for branch in data["branches"]
    }


def test_create_branch_persists_in_postgresql(setup):
    login(setup)

    payload = branch_payload(setup)

    response = setup.client.post(
        "/api/branches",
        json=payload,
    )

    assert response.status_code == 201

    branch = response.json()

    assert branch["code"] == payload["code"].upper()
    assert branch["name"] == payload["name"]
    assert branch["address"] == payload["address"]
    assert branch["is_active"] is True

    with setup.factory() as db:
        row = db.scalar(
            select(Sucursal).where(
                Sucursal.codigo == payload["code"].upper()
            )
        )

        assert row is not None
        assert row.nombre == payload["name"]
        assert row.direccion_local == payload["address"]
        assert row.activa is True


def test_create_branch_normalizes_input(setup):
    login(setup)

    response = setup.client.post(
        "/api/branches",
        json=branch_payload(
            setup,
            code=f"  lower-{setup.suffix[:8]}  ",
            name="  Sucursal normalizada  ",
            address="  Direccion normalizada  ",
        ),
    )

    assert response.status_code == 201

    branch = response.json()

    assert branch["code"] == (
        f"LOWER-{setup.suffix[:8]}".upper()
    )
    assert branch["name"] == "Sucursal normalizada"
    assert branch["address"] == "Direccion normalizada"


def test_duplicate_branch_code_is_rejected(setup):
    login(setup)

    payload = branch_payload(setup)

    first_response = setup.client.post(
        "/api/branches",
        json=payload,
    )

    assert first_response.status_code == 201

    duplicate_response = setup.client.post(
        "/api/branches",
        json={
            **payload,
            "name": "Sucursal duplicada",
            "code": payload["code"].lower(),
        },
    )

    assert duplicate_response.status_code == 409


def test_update_branch_persists_changes(setup):
    login(setup)

    created_response = setup.client.post(
        "/api/branches",
        json=branch_payload(setup),
    )

    assert created_response.status_code == 201

    branch_id = created_response.json()["id"]

    update_response = setup.client.patch(
        f"/api/branches/{branch_id}",
        json={
            "code": f"EDIT-{setup.suffix[:8]}",
            "name": "Sucursal editada",
            "address": "Nueva direccion de prueba",
        },
    )

    assert update_response.status_code == 200

    branch = update_response.json()

    assert branch["code"] == (
        f"EDIT-{setup.suffix[:8]}".upper()
    )
    assert branch["name"] == "Sucursal editada"
    assert branch["address"] == "Nueva direccion de prueba"
    assert branch["is_active"] is True

    with setup.factory() as db:
        row = db.get(
            Sucursal,
            UUID(branch_id),
        )

        assert row is not None
        assert row.codigo == branch["code"]
        assert row.nombre == "Sucursal editada"
        assert (
            row.direccion_local
            == "Nueva direccion de prueba"
        )


def test_update_branch_rejects_duplicate_code(setup):
    login(setup)

    first_response = setup.client.post(
        "/api/branches",
        json=branch_payload(
            setup,
            code=f"FIRST-{setup.suffix[:8]}",
        ),
    )

    second_response = setup.client.post(
        "/api/branches",
        json=branch_payload(
            setup,
            code=f"SECOND-{setup.suffix[:8]}",
            name="Segunda sucursal",
        ),
    )

    assert first_response.status_code == 201
    assert second_response.status_code == 201

    first_id = first_response.json()["id"]
    second_code = second_response.json()["code"]

    response = setup.client.patch(
        f"/api/branches/{first_id}",
        json={
            "code": second_code,
        },
    )

    assert response.status_code == 409


def test_deactivate_branch_without_active_users(setup):
    login(setup)

    created_response = setup.client.post(
        "/api/branches",
        json=branch_payload(setup),
    )

    assert created_response.status_code == 201

    branch_id = created_response.json()["id"]

    deactivate_response = setup.client.post(
        f"/api/branches/{branch_id}/deactivate"
    )

    assert deactivate_response.status_code == 200
    assert deactivate_response.json()["is_active"] is False

    with setup.factory() as db:
        row = db.get(
            Sucursal,
            UUID(branch_id),
        )

        assert row is not None
        assert row.activa is False


def test_deactivate_branch_is_idempotent(setup):
    login(setup)

    created_response = setup.client.post(
        "/api/branches",
        json=branch_payload(setup),
    )

    assert created_response.status_code == 201

    branch_id = created_response.json()["id"]

    first_response = setup.client.post(
        f"/api/branches/{branch_id}/deactivate"
    )

    second_response = setup.client.post(
        f"/api/branches/{branch_id}/deactivate"
    )

    assert first_response.status_code == 200
    assert second_response.status_code == 200
    assert second_response.json()["is_active"] is False


def test_deactivate_branch_with_active_users_is_rejected(setup):
    login(setup)

    response = setup.client.post(
        f"/api/branches/{setup.ids['branch']}/deactivate"
    )

    assert response.status_code == 409

    with setup.factory() as db:
        row = db.get(
            Sucursal,
            setup.ids["branch"],
        )

        assert row is not None
        assert row.activa is True


@pytest.mark.parametrize(
    "field,value",
    [
        ("code", ""),
        ("code", " "),
        ("name", ""),
        ("name", " "),
        ("address", ""),
        ("address", " "),
        ("is_active", "true"),
        ("unknown", "value"),
    ],
)
def test_invalid_branch_create_is_rejected(
    setup,
    field,
    value,
):
    login(setup)

    payload = branch_payload(setup)
    payload[field] = value

    response = setup.client.post(
        "/api/branches",
        json=payload,
    )

    assert response.status_code == 422


@pytest.mark.parametrize(
    "field",
    [
        "code",
        "name",
        "address",
    ],
)
def test_required_create_fields_are_enforced(
    setup,
    field,
):
    login(setup)

    payload = branch_payload(setup)
    del payload[field]

    response = setup.client.post(
        "/api/branches",
        json=payload,
    )

    assert response.status_code == 422


@pytest.mark.parametrize(
    "body",
    [
        {},
        {"code": None},
        {"name": None},
        {"address": None},
        {"code": ""},
        {"name": " "},
        {"address": " "},
        {"is_active": False},
        {"unknown": "value"},
    ],
)
def test_invalid_branch_update_is_rejected(
    setup,
    body,
):
    login(setup)

    response = setup.client.patch(
        f"/api/branches/{setup.ids['branch']}",
        json=body,
    )

    assert response.status_code == 422


@pytest.mark.parametrize(
    "method,path",
    [
        ("GET", ""),
        ("POST", ""),
        ("PATCH", "/target"),
        ("POST", "/target/deactivate"),
        ("POST", "/target/delete"),
    ],
)
def test_anonymous_and_operator_cannot_manage_branches(
    setup,
    method,
    path,
):
    target_path = path.replace(
        "target",
        str(setup.ids["branch"]),
    )

    url = f"/api/branches{target_path}"

    body = None

    if path == "/target/delete":
        body = {"confirmation_id": str(setup.ids["branch"])}

    if method == "POST" and path == "":
        body = branch_payload(setup)

    if method == "PATCH":
        body = {
            "name": "Cambio no permitido",
        }

    anonymous_response = setup.client.request(
        method,
        url,
        json=body,
    )

    assert anonymous_response.status_code == 401

    login(setup, "operator")

    operator_response = setup.client.request(
        method,
        url,
        json=body,
    )

    assert operator_response.status_code == 403


def test_missing_branch_returns_not_found(setup):
    login(setup)

    missing_id = uuid4()

    update_response = setup.client.patch(
        f"/api/branches/{missing_id}",
        json={
            "name": "Sucursal inexistente",
        },
    )

    deactivate_response = setup.client.post(
        f"/api/branches/{missing_id}/deactivate"
    )

    assert update_response.status_code == 404
    assert deactivate_response.status_code == 404


@pytest.mark.parametrize(
    "method,path",
    [
        ("POST", ""),
        ("PATCH", "/target"),
        ("POST", "/target/deactivate"),
        ("POST", "/target/delete"),
    ],
)
def test_untrusted_origin_is_rejected(
    setup,
    method,
    path,
):
    login(setup)

    target_path = path.replace(
        "target",
        str(setup.ids["branch"]),
    )

    url = f"/api/branches{target_path}"

    body = None

    if path == "/target/delete":
        body = {"confirmation_id": str(setup.ids["branch"])}

    if method == "POST" and path == "":
        body = branch_payload(setup)

    if method == "PATCH":
        body = {
            "name": "Cambio externo",
        }

    response = setup.client.request(
        method,
        url,
        json=body,
        headers={
            "Origin": "https://untrusted.example",
        },
    )

    assert response.status_code == 403


@pytest.mark.parametrize("active", [True, False])
def test_delete_unassigned_branch_permanently(setup, active):
    login(setup)
    created = setup.client.post(
        "/api/branches", json=branch_payload(setup, is_active=active),
    )
    assert created.status_code == 201
    branch_id = created.json()["id"]
    response = setup.client.post(
        f"/api/branches/{branch_id}/delete",
        json={"confirmation_id": branch_id},
    )
    assert response.status_code == 204
    assert response.content == b""
    with setup.factory() as db:
        assert db.get(Sucursal, UUID(branch_id)) is None
    assert branch_id not in {
        row["id"] for row in setup.client.get("/api/branches").json()["branches"]
    }
    assert setup.client.post(
        f"/api/branches/{branch_id}/delete", json={"confirmation_id": branch_id},
    ).status_code == 404


@pytest.mark.parametrize("body", [{}, {"confirmation_id": "invalid"},
                                  {"confirmation_id": str(uuid4())}])
def test_delete_requires_matching_confirmation(setup, body):
    login(setup)
    created = setup.client.post("/api/branches", json=branch_payload(setup))
    branch_id = created.json()["id"]
    response = setup.client.post(f"/api/branches/{branch_id}/delete", json=body)
    assert response.status_code == 422
    with setup.factory() as db:
        assert db.get(Sucursal, UUID(branch_id)) is not None


@pytest.mark.parametrize("active", [True, False])
def test_delete_rejects_assigned_users_even_inactive(setup, active):
    login(setup)
    created = setup.client.post("/api/branches", json=branch_payload(setup))
    branch_id = created.json()["id"]
    with setup.factory.begin() as db:
        user = db.get(UsuarioInterno, setup.ids["operator"])
        user.sucursal_id = UUID(branch_id)
        user.activo = active
    listed = setup.client.get("/api/branches").json()["branches"]
    assert next(row for row in listed if row["id"] == branch_id)["can_delete"] is False
    edited = setup.client.patch(
        f"/api/branches/{branch_id}", json={"name": "Sucursal asociada"},
    )
    assert edited.status_code == 200
    assert edited.json()["can_delete"] is False
    response = setup.client.post(
        f"/api/branches/{branch_id}/delete", json={"confirmation_id": branch_id},
    )
    assert response.status_code == 409
    with setup.factory() as db:
        assert db.get(Sucursal, UUID(branch_id)) is not None
        assert db.get(UsuarioInterno, setup.ids["operator"]).sucursal_id == UUID(branch_id)


def test_deletion_availability_updates_after_assignment_and_reassignment(setup):
    login(setup)
    created = setup.client.post("/api/branches", json=branch_payload(setup))
    assert created.status_code == 201
    assert created.json()["can_delete"] is True
    branch_id = created.json()["id"]

    def listed_availability():
        rows = setup.client.get("/api/branches").json()["branches"]
        return next(row for row in rows if row["id"] == branch_id)["can_delete"]

    assert listed_availability() is True
    with setup.factory.begin() as db:
        db.get(UsuarioInterno, setup.ids["operator"]).sucursal_id = UUID(branch_id)
    assert listed_availability() is False
    with setup.factory.begin() as db:
        db.get(UsuarioInterno, setup.ids["operator"]).sucursal_id = setup.ids["branch"]
    assert listed_availability() is True
    deactivated = setup.client.post(f"/api/branches/{branch_id}/deactivate")
    assert deactivated.status_code == 200
    assert deactivated.json()["can_delete"] is True
