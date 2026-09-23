"""Registro y revocación sobre sesion_interna; nunca guarda el JWT original."""

from datetime import datetime, timezone
from hashlib import sha256
from uuid import UUID

from sqlalchemy import select, update
from sqlalchemy.orm import Session, sessionmaker

from app.models import SesionInterna, UsuarioInterno


class SessionRepository:
    def __init__(self, session_factory: sessionmaker[Session]):
        self.session_factory = session_factory

    @staticmethod
    def token_hash(token: str) -> str:
        return sha256(token.encode()).hexdigest()

    def register(self, token: str, user_id: UUID, expires: datetime) -> bool:
        with self.session_factory.begin() as db:
            # Serializa el registro de sesión y la desactivación del usuario.
            user = db.scalar(
                select(UsuarioInterno)
                .where(UsuarioInterno.id == user_id)
                .with_for_update(of=UsuarioInterno)
            )
            if user is None or not user.activo:
                return False
            db.add(
                SesionInterna(
                    usuario_id=user_id,
                    token_hash=self.token_hash(token),
                    creada_en=datetime.now(timezone.utc),
                    expira_en=expires,
                )
            )
        return True

    def active(self, token: str, user_id: UUID) -> bool:
        with self.session_factory() as db:
            return (
                db.scalar(
                    select(SesionInterna.id).where(
                        SesionInterna.token_hash == self.token_hash(token),
                        SesionInterna.usuario_id == user_id,
                        SesionInterna.revocada_en.is_(None),
                        SesionInterna.expira_en > datetime.now(timezone.utc),
                    )
                )
                is not None
            )

    def revoke(self, token: str):
        with self.session_factory.begin() as db:
            db.execute(
                update(SesionInterna)
                .where(
                    SesionInterna.token_hash == self.token_hash(token),
                    SesionInterna.revocada_en.is_(None),
                )
                .values(revocada_en=datetime.now(timezone.utc))
            )
