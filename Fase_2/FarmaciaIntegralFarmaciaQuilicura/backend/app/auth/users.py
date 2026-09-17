import json
import os
import tempfile
from pathlib import Path
from threading import RLock
from typing import Protocol

from pydantic import BaseModel, ConfigDict, EmailStr, Field, TypeAdapter


class User(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)

    id: int = Field(gt=0)
    email: EmailStr
    password_hash: str = Field(pattern=r"^\$argon2id\$")
    is_active: bool
    name: str = ""
    roles: list[str] = Field(default_factory=list)


class DuplicateEmail(Exception):
    pass


class UserNotFound(Exception):
    pass


class UserRepository(Protocol):
    def list_users(self) -> list[User]: ...
    def by_email(self, email: str) -> User | None: ...
    def by_id(self, user_id: int) -> User | None: ...
    def create(
        self,
        *,
        name: str,
        email: str,
        password_hash: str,
        is_active: bool,
        roles: list[str],
    ) -> User: ...
    def update(self, user_id: int, changes: dict) -> User: ...


class LocalUserRepository:
    """Adaptador temporal de desarrollo; sustituir por PostgreSQL posteriormente."""

    def __init__(self, path: Path):
        self.path = path
        self.lock = RLock()
        self._read()

    def _read(self) -> list[User]:
        users = TypeAdapter(list[User]).validate_python(
            json.loads(self.path.read_text(encoding="utf-8"))
        )
        if len({u.id for u in users}) != len(users) or len(
            {u.email.lower() for u in users}
        ) != len(users):
            raise ValueError(
                "El archivo de usuarios contiene identificadores duplicados"
            )
        return users

    def by_email(self, email: str) -> User | None:
        return next(
            (u for u in self.list_users() if u.email.lower() == email.lower()), None
        )

    def by_id(self, user_id: int) -> User | None:
        return next((u for u in self.list_users() if u.id == user_id), None)

    def list_users(self) -> list[User]:
        with self.lock:
            return self._read()

    def _write(self, users: list[User]):
        # El reemplazo atómico evita archivos parciales; el lock cubre un proceso.
        temporary = None
        try:
            with tempfile.NamedTemporaryFile(
                mode="w", encoding="utf-8", dir=self.path.parent, delete=False
            ) as file:
                temporary = Path(file.name)
                json.dump(
                    [u.model_dump(mode="json") for u in users],
                    file,
                    ensure_ascii=False,
                    indent=2,
                )
                file.flush()
                os.fsync(file.fileno())
            os.replace(temporary, self.path)
        finally:
            if temporary is not None:
                temporary.unlink(missing_ok=True)

    def create(
        self,
        *,
        name: str,
        email: str,
        password_hash: str,
        is_active: bool,
        roles: list[str],
    ) -> User:
        with self.lock:
            users = self._read()
            if any(u.email.lower() == email.lower() for u in users):
                raise DuplicateEmail
            user = User(
                id=max((u.id for u in users), default=0) + 1,
                name=name,
                email=email,
                password_hash=password_hash,
                is_active=is_active,
                roles=roles,
            )
            self._write([*users, user])
            return user

    def update(self, user_id: int, changes: dict) -> User:
        with self.lock:
            users = self._read()
            index = next((i for i, u in enumerate(users) if u.id == user_id), None)
            if index is None:
                raise UserNotFound
            user = User.model_validate({**users[index].model_dump(), **changes})
            if any(
                u.id != user_id and u.email.lower() == user.email.lower() for u in users
            ):
                raise DuplicateEmail
            users[index] = user
            self._write(users)
            return user
