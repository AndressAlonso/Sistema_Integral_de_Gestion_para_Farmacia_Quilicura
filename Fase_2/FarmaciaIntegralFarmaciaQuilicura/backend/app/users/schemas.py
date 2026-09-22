from uuid import UUID

from pydantic import (
    BaseModel,
    ConfigDict,
    EmailStr,
    Field,
    field_validator,
    model_validator,
)


class UserFields(BaseModel):
    model_config = ConfigDict(extra="forbid")

    @field_validator(
        "name",
        "email",
        mode="before",
        check_fields=False,
    )
    @classmethod
    def trim(cls, value: object) -> object:
        return value.strip() if isinstance(value, str) else value

    @field_validator(
        "role_ids",
        check_fields=False,
    )
    @classmethod
    def unique_roles(cls, value):
        if (
            value is not None
            and len(value) != len(set(value))
        ):
            raise ValueError("Roles duplicados")

        return value


class CreateUser(UserFields):
    name: str = Field(
        min_length=1,
        max_length=150,
    )
    email: EmailStr = Field(
        max_length=254,
    )
    password: str = Field(
        min_length=12,
        max_length=1024,
    )
    role_ids: list[UUID] = Field(
        min_length=1,
    )
    branch_id: UUID
    is_active: bool = Field(
        strict=True,
    )


class UpdateUser(UserFields):
    name: str | None = Field(
        default=None,
        min_length=1,
        max_length=150,
    )
    email: EmailStr | None = Field(
        default=None,
        max_length=254,
    )
    role_ids: list[UUID] | None = Field(
        default=None,
        min_length=1,
    )
    branch_id: UUID | None = None

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


class UserResponse(BaseModel):
    model_config = ConfigDict(
        from_attributes=True,
    )

    id: UUID
    name: str
    email: EmailStr
    roles: list[str]
    role_ids: list[UUID]
    permissions: list[str]
    branch_id: UUID
    branch_name: str
    is_active: bool


class RoleResponse(BaseModel):
    id: UUID
    code: str
    name: str


class BranchResponse(BaseModel):
    id: UUID
    name: str
    is_active: bool


class UserListResponse(BaseModel):
    users: list[UserResponse]
    roles: list[RoleResponse]
    branches: list[BranchResponse]
    current_user: UserResponse