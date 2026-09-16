import json
from pathlib import Path

from pydantic import BaseModel, ConfigDict, EmailStr, Field, TypeAdapter


class User(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)

    id: int = Field(gt=0)
    email: EmailStr
    password_hash: str = Field(pattern=r"^\$argon2id\$")
    is_active: bool


class LocalUserRepository:
    """Adaptador temporal de desarrollo; sustituir por PostgreSQL posteriormente."""

    def __init__(self, path: Path):
        self.path = path
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
        return next((u for u in self._read() if u.email.lower() == email.lower()), None)

    def by_id(self, user_id: int) -> User | None:
        return next((u for u in self._read() if u.id == user_id), None)
