from typing import NoReturn
from uuid import UUID

from pydantic import BaseModel, ConfigDict
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, sessionmaker

from app.models import Sucursal, UsuarioInterno


class Branch(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)

    id: UUID
    code: str
    name: str
    address: str
    is_active: bool


class DuplicateBranchCode(Exception):
    pass


class BranchNotFound(Exception):
    pass


class BranchInUse(Exception):
    pass


class PostgresBranchRepository:
    def __init__(self, session_factory: sessionmaker[Session]):
        self.session_factory = session_factory

    @staticmethod
    def _to_branch(row: Sucursal) -> Branch:
        return Branch(
            id=row.id,
            code=row.codigo,
            name=row.nombre,
            address=row.direccion_local,
            is_active=row.activa,
        )

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
            rows = db.scalars(
                select(Sucursal).order_by(
                    Sucursal.nombre,
                    Sucursal.id,
                )
            )

            return [self._to_branch(row) for row in rows]

    def by_id(self, branch_id: UUID) -> Branch | None:
        with self.session_factory() as db:
            row = db.get(Sucursal, branch_id)

            return self._to_branch(row) if row else None

    def by_code(self, code: str) -> Branch | None:
        normalized_code = code.strip().upper()

        with self.session_factory() as db:
            row = db.scalar(
                select(Sucursal).where(
                    Sucursal.codigo == normalized_code
                )
            )

            return self._to_branch(row) if row else None

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

                return self._to_branch(row)

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

                return self._to_branch(row)

        except IntegrityError as exc:
            self._integrity_error(exc)

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
                return self._to_branch(row)

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

            return self._to_branch(row)