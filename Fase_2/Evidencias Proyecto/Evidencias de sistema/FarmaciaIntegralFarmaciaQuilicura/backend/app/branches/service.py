from uuid import UUID

from app.auth.users import User
from app.branches.repository import (
    Branch,
    DuplicateBranchCode,
    PostgresBranchRepository,
)
from app.branches.schemas import CreateBranch, UpdateBranch


class AccessDenied(Exception):
    pass


class BranchService:
    def __init__(self, repository: PostgresBranchRepository):
        self.repository = repository

    @staticmethod
    def authorize(actor: User) -> None:
        if (
            not actor.is_active
            or "sucursales.gestionar" not in actor.permissions
        ):
            raise AccessDenied

    def list_branches(self, actor: User):
        self.authorize(actor)
        return self.repository.list_branches()

    def create(
        self,
        actor: User,
        data: CreateBranch,
    ) -> Branch:
        self.authorize(actor)

        if self.repository.by_code(data.code) is not None:
            raise DuplicateBranchCode

        return self.repository.create(
            code=data.code,
            name=data.name,
            address=data.address,
            is_active=data.is_active,
        )

    def update(
        self,
        actor: User,
        branch_id: UUID,
        data: UpdateBranch,
    ) -> Branch:
        self.authorize(actor)

        changes = data.model_dump(exclude_unset=True)

        if "code" in changes:
            existing = self.repository.by_code(changes["code"])

            if existing is not None and existing.id != branch_id:
                raise DuplicateBranchCode

        return self.repository.update(
            branch_id,
            changes,
        )

    def deactivate(
        self,
        actor: User,
        branch_id: UUID,
    ) -> Branch:
        self.authorize(actor)

        return self.repository.deactivate(branch_id)