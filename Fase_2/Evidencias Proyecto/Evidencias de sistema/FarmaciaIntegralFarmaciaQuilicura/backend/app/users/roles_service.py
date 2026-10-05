"""E1-H3: edición de roles y permisos heredados por sus usuarios."""

from uuid import UUID

from sqlalchemy.exc import IntegrityError

from app.auth.users import User
from app.models import Rol
from app.users.roles_repository import RoleRepository
from app.users.schemas import CreateRole, UpdateRole
from app.users.service import AccessDenied


class RoleNotFound(Exception):
    pass


class RoleConflict(Exception):
    pass


class InvalidPermissions(Exception):
    pass


class RoleService:
    required = frozenset({"usuarios.gestionar", "roles.gestionar"})

    def __init__(self, repository: RoleRepository):
        self.repository = repository

    def authorize(self, actor):
        if actor is None or not actor.activo or not self.required <= actor.permisos_efectivos():
            raise AccessDenied

    def catalog(self, actor: User):
        with self.repository.factory() as db:
            self.authorize(self.repository.user(db, actor.id))
            return self.repository.catalog(db)

    def save(self, actor: User, data: CreateRole | UpdateRole, role_id: UUID | None = None):
        try:
            with self.repository.factory.begin() as db:
                self.repository.lock(db)
                self.authorize(self.repository.user(db, actor.id))
                count = 0
                if role_id is None:
                    if data.code in {"ADMIN", "OPERADOR"}:
                        raise RoleConflict("Ese código está reservado por compatibilidad. Utiliza otro.")
                    if self.repository.by_code(db, data.code):
                        raise RoleConflict("Ya existe un rol con ese código.")
                    role = Rol(codigo=data.code, nombre=data.name)
                    db.add(role)
                else:
                    role = self.repository.role(db, role_id)
                    if role is None:
                        raise RoleNotFound
                    count = self.repository.counts(db).get(role.id, 0)
                    if self.repository.public_role(role, count)["revision"] != data.revision:
                        raise RoleConflict("El rol cambió. Recarga la lista antes de guardar.")
                permissions = self.repository.permissions(db, data.permission_ids)
                if len(permissions) != len(data.permission_ids):
                    raise InvalidPermissions
                role.nombre = data.name
                role.permisos = permissions
                db.flush()
                if not any(self.required <= user.permisos_efectivos()
                           for user in self.repository.active_users(db)):
                    raise RoleConflict("Debe quedar al menos una cuenta activa con acceso a usuarios y roles.")
                return self.repository.public_role(role, count)
        except IntegrityError as exc:
            if getattr(exc.orig, "sqlstate", None) == "23505":
                raise RoleConflict("Ya existe un rol con ese código.") from None
            raise
