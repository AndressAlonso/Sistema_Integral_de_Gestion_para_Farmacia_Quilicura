"""E1-H3: persistencia sobre rol/permiso y relaciones existentes."""

from hashlib import sha256
from uuid import UUID

from sqlalchemy import func, select, text
from sqlalchemy.orm import Session, sessionmaker

from app.models import Permiso, Rol, UsuarioInterno, usuario_rol
from app.role_catalog import PERMISSIONS


class RoleRepository:
    def __init__(self, factory: sessionmaker[Session]):
        self.factory = factory

    @staticmethod
    def lock(db: Session):
        # Mismo bloqueo que asignaciones, estado y eliminación de usuarios.
        db.execute(text("SELECT pg_advisory_xact_lock(73412002)"))

    @staticmethod
    def role(db: Session, role_id: UUID):
        return db.get(Rol, role_id)

    @staticmethod
    def by_code(db: Session, code: str):
        return db.scalar(select(Rol).where(Rol.codigo == code))

    @staticmethod
    def permissions(db: Session, ids: list[UUID]):
        return list(db.scalars(select(Permiso).where(Permiso.id.in_(ids))))

    @staticmethod
    def user(db: Session, user_id: UUID):
        return db.get(UsuarioInterno, user_id)

    @staticmethod
    def active_users(db: Session):
        return db.scalars(select(UsuarioInterno).where(UsuarioInterno.activo.is_(True)))

    @staticmethod
    def counts(db: Session):
        return dict(db.execute(select(usuario_rol.c.rol_id, func.count())
                               .group_by(usuario_rol.c.rol_id)).all())

    @staticmethod
    def public_role(row: Rol, count: int):
        ids = sorted(row.permisos, key=lambda permission: str(permission.id))
        # Detecta cambios concurrentes de contenido o número de destinatarios.
        source = f"{row.codigo}\0{row.nombre}\0{count}\0" + ",".join(str(p.id) for p in ids)
        return {
            "id": row.id, "code": row.codigo, "name": row.nombre,
            "permission_ids": [p.id for p in ids], "users_count": count,
            "revision": sha256(source.encode()).hexdigest(),
        }

    def catalog(self, db: Session):
        counts = self.counts(db)
        modules = {
            "usuarios": "Usuarios", "roles": "Roles y permisos",
            "sucursales": "Sucursales", "inventario": "Inventario",
        }
        permissions = []
        for row in db.scalars(select(Permiso).order_by(Permiso.codigo)):
            description, implemented = PERMISSIONS.get(row.codigo, (row.descripcion, False))
            permissions.append({
                "id": row.id, "code": row.codigo, "description": description,
                "implemented": implemented,
                "module": modules.get(row.codigo.split('.')[0], "Otros módulos"),
            })
        return {
            "roles": [self.public_role(row, counts.get(row.id, 0))
                      for row in db.scalars(select(Rol).order_by(Rol.nombre, Rol.id))],
            "permissions": permissions,
        }
