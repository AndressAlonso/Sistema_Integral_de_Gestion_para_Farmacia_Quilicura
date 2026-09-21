from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, Field
from sqlalchemy import select
from sqlalchemy.orm import Session, sessionmaker

from app.models import UsuarioInterno


class User(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)

    id: UUID
    email: EmailStr
    password_hash: str = Field(pattern=r"^\$argon2id\$")
    is_active: bool


class PostgresUserRepository:
    def __init__(self, session_factory: sessionmaker[Session]):
        self.session_factory = session_factory

    @staticmethod
    def _to_user(row: UsuarioInterno | None) -> User | None:
        if row is None:
            return None

        return User(
            id=row.id,
            email=row.correo,
            password_hash=row.password_hash,
            is_active=row.activo,
        )

    def by_email(self, email: str) -> User | None:
        with self.session_factory() as db:
            row = db.scalar(
                select(UsuarioInterno).where(
                    UsuarioInterno.correo == email.strip().lower()
                )
            )
            return self._to_user(row)

    def by_id(self, user_id: UUID) -> User | None:
        with self.session_factory() as db:
            return self._to_user(db.get(UsuarioInterno, user_id))