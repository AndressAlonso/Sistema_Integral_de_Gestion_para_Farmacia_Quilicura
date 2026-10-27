from datetime import datetime, timezone
from uuid import uuid4

import pytest
from sqlalchemy import func, select, text
from sqlalchemy.exc import DBAPIError
from test_auth import login
from test_users import payload

from app.models import EventoAuditoria, Rol, UsuarioInterno


def allow_audit(ctx, code="SOCIO"):
    with ctx.factory.begin() as db:
        role = db.scalar(select(Rol).where(Rol.codigo == code))
        if role is None:
            role = Rol(codigo=code, nombre=code)
            db.add(role)
        user = db.get(UsuarioInterno, ctx.ids["admin"])
        user.roles.append(role)


def test_access_and_validation(setup):
    assert setup.client.get('/api/audit').status_code == 401
    login(setup)
    assert setup.client.get('/api/audit').status_code == 403
    allow_audit(setup)
    assert setup.client.get('/api/audit').status_code == 200
    for query in ('date_from=2026-12-02&date_to=2026-12-01', 'date_from=oops', 'page=0', 'limit=101', 'branch_id=oops'):
        assert setup.client.get('/api/audit?' + query).status_code == 422


def test_filters_inclusive_chile_date_pagination_and_secrets(setup):
    allow_audit(setup, "ADMINISTRADOR")
    login(setup)
    ids = [uuid4() for _ in range(3)]
    with setup.factory.begin() as db:
        for event_id, hour in zip(ids, (2, 3, 23), strict=True):
            db.add(EventoAuditoria(id=event_id, usuario_id=setup.ids['admin'],
                origen_actor='USUARIO_INTERNO', accion='PRUEBA', referencia_historica='Prueba',
                ocurrido_en=datetime(2026, 1, 10, hour, tzinfo=timezone.utc),
                datos_cambio={'sucursal_id': str(setup.ids['branch']), 'usuario_nombre': 'Nombre histórico',
                             'token': 'secreto', 'cambios': {'password_hash': 'secreto'}}))
    query = f"/api/audit?branch_id={setup.ids['branch']}&date_from=2026-01-10&date_to=2026-01-10&limit=1"
    data = setup.client.get(query).json()
    assert data['total'] == 2
    assert data['events'][0]['id'] == str(ids[2])
    assert 'secreto' not in str(data)
    assert setup.client.get(query + '&page=2').json()['events'][0]['id'] == str(ids[1])
    assert setup.client.get(query.replace(str(setup.ids['branch']), str(uuid4()))).json()['total'] == 0


def test_http_change_atomic_and_actor_snapshot(setup):
    allow_audit(setup)
    login(setup)
    response = setup.client.post('/api/users', json=payload(setup))
    assert response.status_code == 201, response.text
    target = response.json()['id']
    with setup.factory() as db:
        event = db.scalar(select(EventoAuditoria).where(
            EventoAuditoria.datos_cambio['entidad_id'].astext == target,
            EventoAuditoria.accion == 'usuario_interno.creado'))
        assert event is not None
        assert event.datos_cambio['usuario_nombre'] == 'Fixture admin'
        assert event.datos_cambio['sucursal_id'] == str(setup.ids['branch'])
        assert 'password' not in str(event.datos_cambio)
        count = db.scalar(select(func.count()).select_from(EventoAuditoria))
    assert setup.client.post('/api/users', json=payload(setup)).status_code == 409
    with setup.factory() as db:
        assert db.scalar(select(func.count()).select_from(EventoAuditoria)) == count


def test_actor_deletion_keeps_name_and_immutable_event(setup):
    allow_audit(setup)
    with setup.factory.begin() as db:
        actor = db.get(UsuarioInterno, setup.ids['manager'])
        actor.roles.append(db.get(Rol, setup.ids['admin_role']))
    login(setup, 'manager')
    assert setup.client.patch(f"/api/users/{setup.ids['operator']}", json={'name': 'Nuevo nombre'}).status_code == 200
    with setup.factory() as db:
        event = db.scalar(select(EventoAuditoria).where(EventoAuditoria.usuario_id == setup.ids['manager']))
        assert event is not None
        event_id = event.id
    login(setup)
    response = setup.client.post(f"/api/users/{setup.ids['manager']}/delete", json={'confirmation_email': setup.emails['manager']})
    assert response.status_code == 204, response.text
    with setup.factory() as db:
        assert db.get(UsuarioInterno, setup.ids['manager']) is None
        assert db.get(EventoAuditoria, event_id).datos_cambio['usuario_nombre'] == 'Fixture manager'
    for statement in ('DELETE FROM evento_auditoria WHERE id=:id', "UPDATE evento_auditoria SET accion='ALTERADO' WHERE id=:id"):
        with pytest.raises(DBAPIError), setup.factory.begin() as db:
            db.execute(text(statement), {'id': event_id})
