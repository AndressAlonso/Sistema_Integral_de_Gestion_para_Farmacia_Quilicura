"""E1-H2: reglas independientes del adaptador de persistencia."""

from uuid import UUID

from app.auth.security import password_hasher
from app.auth.users import DuplicateEmail, PostgresUserRepository, User, UserNotFound
from app.users.schemas import CreateUser, UpdateUser


class AccessDenied(Exception):
    pass


class UserService:
    def __init__(self, repository: PostgresUserRepository):
        self.repository = repository

    @staticmethod
    def authorize(actor: User):
        if not actor.is_active or "usuarios.gestionar" not in actor.permissions:
            raise AccessDenied

    def list_users(self, actor: User) -> list[User]:
        self.authorize(actor)
        return self.repository.list_users()

    def create(self, actor: User, data: CreateUser) -> User:
        self.authorize(actor)
        if "roles.gestionar" not in actor.permissions:
            raise AccessDenied
        if self.repository.by_email(str(data.email)):
            raise DuplicateEmail
        return self.repository.create(
            name=data.name,
            email=str(data.email).lower(),
            password_hash=password_hasher.hash(data.password),
            is_active=data.is_active,
            role_ids=data.role_ids,
            branch_id=data.branch_id,
        )

    def update(self, actor: User, user_id: UUID, data: UpdateUser) -> User:
        self.authorize(actor)
        target = self.repository.by_id(user_id)
        if target is None:
            raise UserNotFound
        changes = data.model_dump(exclude_unset=True)
        if "role_ids" in changes and "roles.gestionar" not in actor.permissions:
            if set(changes["role_ids"]) != set(target.role_ids):
                raise AccessDenied
            del changes["role_ids"]
        if "email" in changes:
            changes["email"] = str(changes["email"]).lower()
            existing = self.repository.by_email(changes["email"])
            if existing and existing.id != user_id:
                raise DuplicateEmail
        # PostgreSQL garantiza unicidad incluso ante escrituras simultáneas.
        return self.repository.update(user_id, changes)

    def deactivate(self, actor: User, user_id: UUID) -> User:
        self.authorize(actor)
        return self.repository.update(user_id, {"is_active": False})
