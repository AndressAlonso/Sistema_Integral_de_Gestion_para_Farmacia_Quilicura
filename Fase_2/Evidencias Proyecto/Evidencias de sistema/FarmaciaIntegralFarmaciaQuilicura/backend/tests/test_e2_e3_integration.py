"""Regresión de integración E1/E2-H1/E3-H1 con rollback PostgreSQL."""

from uuid import UUID

import pytest
from sqlalchemy import delete, select
from sqlalchemy.exc import IntegrityError
from test_auth import login

from app.models import InventarioSucursal, Permiso, Rol, Sucursal, rol_permiso
from app.role_catalog import ADMIN_ROLE
from app.seed_e2_e3 import seed_permissions


@pytest.fixture
def integrated(setup):
    with setup.factory.begin() as db:
        role = db.get(Rol, setup.ids["admin_role"])
        for code in ("catalogo.gestionar", "inventario.consultar"):
            permission = db.scalar(select(Permiso).where(Permiso.codigo == code))
            if permission is None:
                permission = Permiso(codigo=code, descripcion="Prueba temporal")
                db.add(permission)
            role.permisos.append(permission)
    assert login(setup).status_code == 200
    category = setup.client.post("/api/categories", json={"name": "Integración"})
    assert category.status_code == 201
    product = setup.client.post("/api/products", json={
        "sku": "INT-" + setup.suffix, "name": "Producto integrado",
        "category_id": category.json()["id"], "price": "1000.00",
        "requires_prescription": False, "barcodes": [setup.suffix],
    })
    assert product.status_code == 201
    setup.product_id = UUID(product.json()["id"])
    with setup.factory.begin() as db:
        branch = Sucursal(
            codigo="INT-" + setup.suffix[:16], nombre="Sucursal sin usuarios",
            direccion_local="Dirección ficticia", activa=True,
        )
        db.add(branch)
        db.flush()
        record = InventarioSucursal(
            producto_id=setup.product_id, sucursal_id=branch.id,
            stock_fisico=12, stock_reservado=4,
        )
        db.add(record)
        db.flush()
        setup.inventory_id, setup.inventory_branch_id = record.id, branch.id
    return setup


def test_catalog_product_and_branch_reach_inventory(integrated):
    response = integrated.client.get("/api/inventory")
    assert response.status_code == 200
    record = next(r for r in response.json()["records"]
                  if r["id"] == str(integrated.inventory_id))
    assert record["product_id"] == str(integrated.product_id)
    assert record["product_name"] == "Producto integrado"
    assert record["branch_id"] == str(integrated.inventory_branch_id)
    assert (record["physical"], record["reserved"], record["available"]) == (12, 4, 8)
    permissions = integrated.client.get("/api/users/roles").json()["permissions"]
    for code in ("catalogo.gestionar", "inventario.consultar"):
        assert next(p for p in permissions if p["code"] == code)["implemented"]


@pytest.mark.parametrize("endpoint", ["/api/products", "/api/categories", "/api/inventory"])
def test_protected_modules_require_session_and_permission(setup, endpoint):
    assert setup.client.get(endpoint).status_code == 401
    assert login(setup, "operator").status_code == 200
    assert setup.client.get(endpoint).status_code == 403


def test_branch_with_inventory_cannot_be_deleted(integrated):
    branch_id = str(integrated.inventory_branch_id)
    branches = integrated.client.get("/api/branches").json()["branches"]
    branch = next(b for b in branches if b["id"] == branch_id)
    assert branch["assigned_users_count"] == 0
    assert branch["can_delete"] is False
    response = integrated.client.post(
        f"/api/branches/{branch_id}/delete", json={"confirmation_id": branch_id},
    )
    assert response.status_code == 409
    with integrated.factory() as db:
        assert db.get(Sucursal, integrated.inventory_branch_id) is not None
        assert db.get(InventarioSucursal, integrated.inventory_id).stock_fisico == 12


@pytest.mark.parametrize("physical,reserved", [(-1, 0), (1, -1), (1, 2)])
def test_database_rejects_invalid_stock(integrated, physical, reserved):
    with pytest.raises(IntegrityError), integrated.factory.begin() as db:
        record = db.get(InventarioSucursal, integrated.inventory_id)
        record.stock_fisico, record.stock_reservado = physical, reserved
        db.flush()
    with integrated.factory() as db:
        record = db.get(InventarioSucursal, integrated.inventory_id)
        assert (record.stock_fisico, record.stock_reservado) == (12, 4)


def test_seed_adds_catalog_once_and_preserves_customized_roles(setup):
    with setup.factory.begin() as db:
        permission = db.scalar(select(Permiso).where(Permiso.codigo == "catalogo.gestionar"))
        if permission is not None:
            db.execute(delete(rol_permiso).where(rol_permiso.c.permiso_id == permission.id))
            db.delete(permission)
            db.flush()
        admin = db.scalar(select(Rol).where(Rol.codigo == ADMIN_ROLE))
        if admin is None:
            admin = Rol(codigo=ADMIN_ROLE, nombre="Administrador personalizado")
            db.add(admin)
        admin.nombre = "Administrador personalizado"
        admin.permisos = []
        db.flush()
        admin_id = admin.id
        seed_permissions(db)
        assert [p.codigo for p in admin.permisos] == ["catalogo.gestionar"]
        assert admin.id == admin_id
        assert admin.nombre == "Administrador personalizado"
        admin.permisos = []
        db.flush()
        seed_permissions(db)
        assert admin.permisos == []
