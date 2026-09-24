from uuid import UUID

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    field_validator,
    model_validator,
)


class BranchFields(BaseModel):
    model_config = ConfigDict(extra="forbid")

    @field_validator(
        "code",
        "name",
        "address",
        mode="before",
        check_fields=False,
    )
    @classmethod
    def trim_text(cls, value: object) -> object:
        if isinstance(value, str):
            return value.strip()

        return value

    @field_validator(
        "code",
        check_fields=False,
    )
    @classmethod
    def normalize_code(
        cls,
        value: str | None,
    ) -> str | None:
        if isinstance(value, str):
            return value.upper()

        return value


class CreateBranch(BranchFields):
    code: str = Field(
        min_length=1,
        max_length=30,
    )
    name: str = Field(
        min_length=1,
        max_length=150,
    )
    address: str = Field(
        min_length=1,
        max_length=250,
    )
    is_active: bool = Field(
        default=True,
        strict=True,
    )


class UpdateBranch(BranchFields):
    code: str | None = Field(
        default=None,
        min_length=1,
        max_length=30,
    )
    name: str | None = Field(
        default=None,
        min_length=1,
        max_length=150,
    )
    address: str | None = Field(
        default=None,
        min_length=1,
        max_length=250,
    )

    @model_validator(mode="after")
    def valid_patch(self):
        if not self.model_fields_set:
            raise ValueError(
                "Actualización vacía"
            )

        if any(
            getattr(self, field) is None
            for field in self.model_fields_set
        ):
            raise ValueError(
                "Los campos enviados no pueden ser nulos"
            )

        return self


class BranchResponse(BaseModel):
    model_config = ConfigDict(
        from_attributes=True,
    )

    id: UUID
    code: str
    name: str
    address: str
    is_active: bool
    can_delete: bool
    assigned_users_count: int = Field(ge=0)


class BranchListResponse(BaseModel):
    branches: list[BranchResponse]


class DeleteBranch(BaseModel):
    model_config = ConfigDict(extra="forbid")

    confirmation_id: UUID


class AssignedUserResponse(BaseModel):
    id: UUID
    name: str
    email: str
    roles: list[str]
    is_active: bool


class AssignedUserListResponse(BaseModel):
    users: list[AssignedUserResponse]
