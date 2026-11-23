from sqlalchemy import event
from sqlalchemy.orm import sessionmaker

from app.audit.recording import audit_listener, record_changes


def test_nested_apps_keep_audit_until_last_owner_exits():
    factory = sessionmaker()
    assert not event.contains(factory, "before_flush", record_changes)
    with audit_listener(factory):
        with audit_listener(factory):
            assert event.contains(factory, "before_flush", record_changes)
        assert event.contains(factory, "before_flush", record_changes)
    assert not event.contains(factory, "before_flush", record_changes)
