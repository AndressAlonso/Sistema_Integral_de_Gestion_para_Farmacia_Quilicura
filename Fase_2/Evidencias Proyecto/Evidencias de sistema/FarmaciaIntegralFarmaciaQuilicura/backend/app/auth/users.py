"""Persistencia E1-H1/E1-H2 sobre el modelo PostgreSQL existente."""

from datetime import datetime, timezone
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, Field
from sqlalchemy import delete, func, select, text, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, sessionmaker

from app.models import Rol, SesionInterna, Sucursal, UsuarioInterno
from app.role_catalog import ADMIN_ROLE, PERMISSIONS, ROLE_CATALOG


class User(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
        strict=True,
    )

    id: UUID
    email: EmailStr
    password_hash: str = Field(
        pattern=r"^\$argon2id\$",
    )
    is_active: bool
    name: str
    roles: list[str]
    role_ids: list[UUID]
    permissions: list[str]
    branch_id: UUID
    branch_name: str


class DuplicateEmail(Exception):
    pass


class UserNotFound(Exception):
    pass


class InvalidReference(Exception):
    pass


class UserDeletionBlocked(Exception):
    pass


class InvalidDeletionConfirmation(Exception):
    pass


class PostgresUserRepository:
    def __init__(
        self,
        session_factory: sessionmaker[Session],
    ):
        self.session_factory = session_factory

    @staticmethod
    def _lock_access_changes(db: Session) -> None:
        # Serializa cambios de estado/roles y borrados que protegen al último administrador.
        db.execute(text("SELECT pg_advisory_xact_lock(73412002)"))

    @staticmethod
    def _deletion_reason(row, actor_id, active_admins):
        if row.id == actor_id:
            return "No puedes eliminar tu propia cuenta."
        if row.activo and any(role.codigo == ADMIN_ROLE for role in row.roles) and active_admins <= 1:
            return "No se puede eliminar al último administrador activo."
        return None

    @staticmethod
    def _active_admin_count(db: Session) -> int:
        return db.scalar(select(func.count()).select_from(UsuarioInterno).where(
            UsuarioInterno.activo.is_(True),
            UsuarioInterno.roles.any(Rol.codigo == ADMIN_ROLE),
        ))

    def deletion_options(self, actor_id: UUID) -> dict:
        with self.session_factory() as db:
            active_admins = self._active_admin_count(db)
            rows = db.scalars(select(UsuarioInterno))
            return {
                row.id: self._deletion_reason(row, actor_id, active_admins)
                for row in rows
            }

    def delete(self, actor_id: UUID, user_id: UUID, confirmation_email: str) -> None:
        try:
            with self.session_factory.begin() as db:
                self._lock_access_changes(db)
                row = db.scalar(select(UsuarioInterno).where(
                    UsuarioInterno.id == user_id,
                ).with_for_update(of=UsuarioInterno))
                if row is None:
                    raise UserNotFound
                if row.correo != confirmation_email.strip().lower():
                    raise InvalidDeletionConfirmation
                reason = self._deletion_reason(
                    row, actor_id, self._active_admin_count(db),
                )
                if reason:
                    raise UserDeletionBlocked(reason)
                db.execute(delete(SesionInterna).where(SesionInterna.usuario_id == user_id))
                row.roles.clear()
                db.flush()
                db.delete(row)
                db.flush()
        except IntegrityError as exc:
            if getattr(exc.orig, "sqlstate", None) == "23503":
                raise UserDeletionBlocked(
                    "El usuario tiene registros asociados. Utiliza Desactivar."
                ) from None
            raise

    @staticmethod
    def _to_user(row: UsuarioInterno) -> User:
        roles = sorted(
            row.roles,
            key=lambda role: role.codigo,
        )

        return User(
            id=row.id,
            email=row.correo,
            password_hash=row.password_hash,
            is_active=row.activo,
            name=row.nombre,
            roles=[
                role.codigo
                for role in roles
            ],
            role_ids=[
                role.id
                for role in roles
            ],
            permissions=sorted(
                row.permisos_efectivos()
            ),
            branch_id=row.sucursal_id,
            branch_name=row.sucursal.nombre,
        )

    def by_email(
        self,
        email: str,
    ) -> User | None:
        normalized_email = email.strip().lower()

        with self.session_factory() as db:
            row = db.scalar(
                select(UsuarioInterno).where(
                    UsuarioInterno.correo
                    == normalized_email
                )
            )

            return (
                self._to_user(row)
                if row
                else None
            )

    def by_id(
        self,
        user_id: UUID,
    ) -> User | None:
        with self.session_factory() as db:
            row = db.get(
                UsuarioInterno,
                user_id,
            )

            return (
                self._to_user(row)
                if row
                else None
            )

    def list_users(self):
        with self.session_factory() as db:
            rows = db.scalars(
                select(UsuarioInterno).order_by(
                    UsuarioInterno.nombre,
                    UsuarioInterno.id,
                )
            )

            return [
                self._to_user(row)
                for row in rows
            ]

    def options(self) -> dict:
        with self.session_factory() as db:
            roles = db.scalars(
                select(Rol).order_by(
                    Rol.nombre,
                    Rol.id,
                )
            )

            branches = db.scalars(
                select(Sucursal).order_by(
                    Sucursal.nombre,
                    Sucursal.id,
                )
            )

            return {
                "roles": [
                    {
                        "id": role.id,
                        "code": role.codigo,
                        "name": role.nombre,
                        "description": ROLE_CATALOG[role.codigo].description
                        if role.codigo in ROLE_CATALOG else "Rol personalizado del sistema.",
                        "permissions": [
                            {
                                "code": permission.codigo,
                                "description": PERMISSIONS.get(
                                    permission.codigo, (permission.descripcion, False)
                                )[0],
                                "implemented": PERMISSIONS.get(
                                    permission.codigo, (permission.descripcion, False)
                                )[1],
                            }
                            for permission in sorted(role.permisos, key=lambda item: item.codigo)
                        ],
                    }
                    for role in roles
                ],
                "branches": [
                    {
                        "id": branch.id,
                        "name": branch.nombre,
                        "is_active": branch.activa,
                    }
                    for branch in branches
                ],
            }

    @staticmethod
    def _roles(
        db: Session,
        ids: list[UUID],
    ):
        roles = list(
            db.scalars(
                select(Rol).where(
                    Rol.id.in_(ids)
                )
            )
        )

        if len(roles) != len(ids):
            raise InvalidReference

        return roles

    @staticmethod
    def _active_branch(
        db: Session,
        branch_id: UUID,
    ) -> Sucursal:
        branch = db.get(
            Sucursal,
            branch_id,
        )

        if branch is None or not branch.activa:
            raise InvalidReference

        return branch

    @staticmethod
    def _integrity_error(
        exc: IntegrityError,
    ):
        sqlstate = getattr(
            exc.orig,
            "sqlstate",
            None,
        )

        constraint_name = getattr(
            getattr(
                exc.orig,
                "diag",
                None,
            ),
            "constraint_name",
            None,
        )

        if (
            sqlstate == "23505"
            and constraint_name
            == "usuario_interno_correo_key"
        ):
            raise DuplicateEmail from None

        if sqlstate == "23503":
            raise InvalidReference from None

        raise exc

    def create(
        self,
        *,
        name: str,
        email: str,
        password_hash: str,
        is_active: bool,
        role_ids: list[UUID],
        branch_id: UUID,
    ) -> User:
        try:
            with self.session_factory.begin() as db:
                branch = self._active_branch(
                    db,
                    branch_id,
                )

                row = UsuarioInterno(
                    nombre=name,
                    correo=email.lower(),
                    password_hash=password_hash,
                    activo=is_active,
                    sucursal=branch,
                    roles=self._roles(
                        db,
                        role_ids,
                    ),
                )

                db.add(row)
                db.flush()

                return self._to_user(row)

        except IntegrityError as exc:
            self._integrity_error(exc)

    def update(
        self,
        user_id: UUID,
        changes: dict,
    ) -> User:
        try:
            with self.session_factory.begin() as db:
                self._lock_access_changes(db)
                row = db.scalar(
                    select(UsuarioInterno)
                    .where(
                        UsuarioInterno.id
                        == user_id
                    )
                    .with_for_update(
                        of=UsuarioInterno
                    )
                )

                if row is None:
                    raise UserNotFound

                if "name" in changes:
                    row.nombre = changes["name"]

                if "email" in changes:
                    row.correo = changes[
                        "email"
                    ].lower()

                if "role_ids" in changes:
                    row.roles = self._roles(
                        db,
                        changes["role_ids"],
                    )

                if "branch_id" in changes:
                    branch = self._active_branch(
                        db,
                        changes["branch_id"],
                    )

                    row.sucursal = branch
                    row.sucursal_id = branch.id

                if "is_active" in changes:
                    row.activo = changes[
                        "is_active"
                    ]

                    if not row.activo:
                        db.execute(
                            update(SesionInterna)
                            .where(
                                SesionInterna.usuario_id
                                == user_id,
                                SesionInterna.revocada_en.is_(
                                    None
                                ),
                            )
                            .values(
                                revocada_en=datetime.now(
                                    timezone.utc
                                )
                            )
                        )

                db.flush()

                return self._to_user(row)

        except IntegrityError as exc:
            self._integrity_error(exc)
