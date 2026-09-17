from typing import Literal

from pydantic import (
    BaseModel,
    ConfigDict,
    EmailStr,
    Field,
    field_validator,
    model_validator,
)

RoleCode = Literal["ADMINISTRADOR", "CAJERO"]


class UserFields(BaseModel):
    model_config = ConfigDict(extra="forbid")

    @field_validator("name", "email", mode="before", check_fields=False)
    @classmethod
    def trim(cls, value: object) -> object:
        return value.strip() if isinstance(value, str) else value

    @field_validator("roles", check_fields=False)
    @classmethod
    def unique_roles(cls, value):
        if value is not None and len(value) != len(set(value)):
            raise ValueError("Roles duplicados")
        return value


class CreateUser(UserFields):
    name: str = Field(min_length=1, max_length=120)
    email: EmailStr = Field(max_length=254)
    password: str = Field(min_length=12, max_length=1024)
    roles: list[RoleCode] = Field(min_length=1, max_length=2)
    is_active: bool = Field(strict=True)


class UpdateUser(UserFields):
    name: str | None = Field(default=None, min_length=1, max_length=120)
    email: EmailStr | None = Field(default=None, max_length=254)
    roles: list[RoleCode] | None = Field(default=None, min_length=1, max_length=2)

    @model_validator(mode="after")
    def valid_patch(self):
        if not self.model_fields_set or any(
            getattr(self, field) is None for field in self.model_fields_set
        ):
            raise ValueError("Actualización vacía o nula")
        return self


class UserResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    name: str
    email: EmailStr
    roles: list[str]
    is_active: bool


class RoleResponse(BaseModel):
    code: str
    name: str


class UserListResponse(BaseModel):
    users: list[UserResponse]
    roles: list[RoleResponse]
    current_user: UserResponse
