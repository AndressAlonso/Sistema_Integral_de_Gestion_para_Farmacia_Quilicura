"""E1-H2: reglas independientes del adaptador de persistencia."""

from app.auth.security import password_hasher
from app.auth.users import DuplicateEmail, User, UserNotFound, UserRepository
from app.users.schemas import CreateUser, UpdateUser

# Catálogo temporal para E1-H2; no implementa administración de roles (E1-H3).
ROLES = [
    {"code": "ADMINISTRADOR", "name": "Administrador"},
    {"code": "CAJERO", "name": "Cajero"},
]


class AccessDenied(Exception):
    pass


class UserService:
    def __init__(self, repository: UserRepository):
        self.repository = repository

    @staticmethod
    def authorize(actor: User):
        if not actor.is_active or "ADMINISTRADOR" not in actor.roles:
            raise AccessDenied

    def list_users(self, actor: User) -> list[User]:
        self.authorize(actor)
        return self.repository.list_users()

    def create(self, actor: User, data: CreateUser) -> User:
        self.authorize(actor)
        if self.repository.by_email(str(data.email)):
            raise DuplicateEmail
        return self.repository.create(
            name=data.name,
            email=str(data.email).lower(),
            password_hash=password_hasher.hash(data.password),
            is_active=data.is_active,
            roles=list(data.roles),
        )

    def update(self, actor: User, user_id: int, data: UpdateUser) -> User:
        self.authorize(actor)
        if self.repository.by_id(user_id) is None:
            raise UserNotFound
        changes = data.model_dump(exclude_unset=True)
        if "email" in changes:
            changes["email"] = str(changes["email"]).lower()
            existing = self.repository.by_email(changes["email"])
            if existing and existing.id != user_id:
                raise DuplicateEmail
        # Repositorio vuelve a comprobar unicidad dentro de la escritura atómica.
        return self.repository.update(user_id, changes)

    def deactivate(self, actor: User, user_id: int) -> User:
        self.authorize(actor)
        return self.repository.update(user_id, {"is_active": False})
