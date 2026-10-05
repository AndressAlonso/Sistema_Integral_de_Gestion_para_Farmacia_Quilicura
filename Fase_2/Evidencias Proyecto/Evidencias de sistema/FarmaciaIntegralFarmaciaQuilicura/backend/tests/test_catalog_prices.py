"""E2-H2: rollback del precio y protección de su auditoría."""

import pytest
from sqlalchemy import text
from sqlalchemy.exc import DBAPIError

pytest_plugins = ["test_catalog_images"]


def test_price_and_audit_roll_back_together(catalog, monkeypatch):
    repository = catalog.app.state.catalog
    original_response = repository.response

    def fail_after_flush(row):
        raise RuntimeError("Fallo simulado después de guardar")

    with monkeypatch.context() as patch:
        patch.setattr(repository, "response", fail_after_flush)

        result = catalog.client.patch(
            catalog.url + "/price",
            json={
                "price": "2490.00",
                "expected_price": catalog.payload["price"],
            },
        )

    assert result.status_code == 500
    assert repository.response == original_response

    product = catalog.client.get(catalog.url)
    assert product.status_code == 200
    assert product.json()["price"] == catalog.payload["price"]

    history = catalog.client.get(catalog.url + "/price-history")
    assert history.status_code == 200
    assert history.json() == []


@pytest.mark.parametrize(
    "statement",
    [
        (
            "UPDATE evento_auditoria "
            "SET accion = 'alterado' WHERE id = :event_id"
        ),
        "DELETE FROM evento_auditoria WHERE id = :event_id",
    ],
)
def test_price_audit_cannot_be_changed_or_deleted(catalog, statement):
    result = catalog.client.patch(
        catalog.url + "/price",
        json={
            "price": "2490.00",
            "expected_price": catalog.payload["price"],
        },
    )
    assert result.status_code == 200

    history = catalog.client.get(catalog.url + "/price-history")
    assert history.status_code == 200
    before = history.json()
    assert len(before) == 1

    with pytest.raises(DBAPIError) as error, catalog.factory.begin() as db:
        db.execute(
            text(statement),
            {"event_id": before[0]["id"]},
        )

    assert getattr(error.value.orig, "sqlstate", None) == "55000"

    after = catalog.client.get(catalog.url + "/price-history")
    assert after.status_code == 200
    assert after.json() == before