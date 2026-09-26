from typing import NoReturn
from uuid import UUID

from pydantic import BaseModel, ConfigDict
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, sessionmaker

from app.models import InventarioSucursal, Sucursal, UsuarioInterno


class Branch(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)

    id: UUID
    code: str
    name: str
    address: str
    is_active: bool
    can_delete: bool = False
    assigned_users_count: int = 0


class DuplicateBranchCode(Exception):
    pass


class BranchNotFound(Exception):
    pass


class BranchInUse(Exception):
    pass


class BranchDeletionBlocked(Exception):
    pass


class PostgresBranchRepository:
    def __init__(self, session_factory: sessionmaker[Session]):
        self.session_factory = session_factory

    @staticmethod
    def _to_branch(
        row: Sucursal, assigned_users_count: int, has_inventory: bool,
    ) -> Branch:
        return Branch(
            id=row.id,
            code=row.codigo,
            name=row.nombre,
            address=row.direccion_local,
            is_active=row.activa,
            can_delete=assigned_users_count == 0 and not has_inventory,
            assigned_users_count=assigned_users_count,
        )

    @staticmethod
    def _has_users(branch_id):
        return select(UsuarioInterno.id).where(
            UsuarioInterno.sucursal_id == branch_id
        ).exists()

    @staticmethod
    def _has_inventory(branch_id):
        return select(InventarioSucursal.id).where(
            InventarioSucursal.sucursal_id == branch_id
        ).exists()

    def _can_delete(self, db: Session, branch_id: UUID) -> bool:
        return not db.scalar(select(
            self._has_users(branch_id) | self._has_inventory(branch_id)
        ))

    def _branch(self, db: Session, row: Sucursal) -> Branch:
        return self._to_branch(
            row, self._user_count(db, row.id),
            bool(db.scalar(select(self._has_inventory(row.id)))),
        )

    @staticmethod
    def _user_count(db: Session, branch_id: UUID) -> int:
        return db.scalar(select(func.count()).select_from(UsuarioInterno).where(
            UsuarioInterno.sucursal_id == branch_id,
        ))

    @staticmethod
    def _integrity_error(exc: IntegrityError) -> NoReturn:
        sqlstate = getattr(exc.orig, "sqlstate", None)
        constraint = getattr(
            getattr(exc.orig, "diag", None),
            "constraint_name",
            None,
        )

        if sqlstate == "23505" and constraint == "sucursal_codigo_key":
            raise DuplicateBranchCode from None

        raise exc

    def list_branches(self):
        with self.session_factory() as db:
            rows = db.execute(
                select(
                    Sucursal,
                    select(func.count()).select_from(UsuarioInterno)
                    .where(UsuarioInterno.sucursal_id == Sucursal.id)
                    .correlate(Sucursal).scalar_subquery(),
                    self._has_inventory(Sucursal.id),
                ).order_by(
                    Sucursal.nombre,
                    Sucursal.id,
                )
            )

            return [self._to_branch(row, count, inventory) for row, count, inventory in rows]

    def assigned_users(self, branch_id: UUID) -> list[dict]:
        with self.session_factory() as db:
            if db.get(Sucursal, branch_id) is None:
                raise BranchNotFound
            rows = db.scalars(select(UsuarioInterno).where(
                UsuarioInterno.sucursal_id == branch_id,
            ).order_by(UsuarioInterno.nombre, UsuarioInterno.id))
            return [{
                "id": row.id, "name": row.nombre, "email": row.correo,
                "roles": sorted(role.nombre for role in row.roles),
                "is_active": row.activo,
            } for row in rows]

    def by_id(self, branch_id: UUID) -> Branch | None:
        with self.session_factory() as db:
            row = db.get(Sucursal, branch_id)

            return self._branch(db, row) if row else None

    def by_code(self, code: str) -> Branch | None:
        normalized_code = code.strip().upper()

        with self.session_factory() as db:
            row = db.scalar(
                select(Sucursal).where(
                    Sucursal.codigo == normalized_code
                )
            )

            return self._branch(db, row) if row else None

    def create(
        self,
        *,
        code: str,
        name: str,
        address: str,
        is_active: bool,
    ) -> Branch:
        try:
            with self.session_factory.begin() as db:
                row = Sucursal(
                    codigo=code.strip().upper(),
                    nombre=name.strip(),
                    direccion_local=address.strip(),
                    activa=is_active,
                )

                db.add(row)
                db.flush()

                return self._branch(db, row)

        except IntegrityError as exc:
            self._integrity_error(exc)

    def update(
        self,
        branch_id: UUID,
        changes: dict,
    ) -> Branch:
        try:
            with self.session_factory.begin() as db:
                row = db.scalar(
                    select(Sucursal)
                    .where(Sucursal.id == branch_id)
                    .with_for_update(of=Sucursal)
                )

                if row is None:
                    raise BranchNotFound

                if "code" in changes:
                    row.codigo = changes["code"].strip().upper()

                if "name" in changes:
                    row.nombre = changes["name"].strip()

                if "address" in changes:
                    row.direccion_local = changes["address"].strip()

                db.flush()

                return self._branch(db, row)

        except IntegrityError as exc:
            self._integrity_error(exc)

    def activate(self, branch_id: UUID) -> Branch:
        with self.session_factory.begin() as db:
            row = db.scalar(select(Sucursal).where(
                Sucursal.id == branch_id,
            ).with_for_update(of=Sucursal))
            if row is None:
                raise BranchNotFound
            row.activa = True
            db.flush()
            return self._branch(db, row)

    def deactivate(self, branch_id: UUID) -> Branch:
        with self.session_factory.begin() as db:
            row = db.scalar(
                select(Sucursal)
                .where(Sucursal.id == branch_id)
                .with_for_update(of=Sucursal)
            )

            if row is None:
                raise BranchNotFound

            if not row.activa:
                return self._branch(db, row)

            active_users = db.scalar(
                select(func.count())
                .select_from(UsuarioInterno)
                .where(
                    UsuarioInterno.sucursal_id == branch_id,
                    UsuarioInterno.activo.is_(True),
                )
            )

            if active_users is not None and active_users > 0:
                raise BranchInUse

            row.activa = False
            db.flush()

            return self._branch(db, row)

    def delete(self, branch_id: UUID) -> None:
        try:
            with self.session_factory.begin() as db:
                row = db.scalar(
                    select(Sucursal)
                    .where(Sucursal.id == branch_id)
                    .with_for_update(of=Sucursal)
                )
                if row is None:
                    raise BranchNotFound
                if not self._can_delete(db, branch_id):
                    raise BranchDeletionBlocked
                db.delete(row)
                db.flush()
        except IntegrityError as exc:
            # Las FK también protegen frente a asignaciones concurrentes.
            if getattr(exc.orig, "sqlstate", None) == "23503":
                raise BranchDeletionBlocked from None
            raise
