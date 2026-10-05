from pathlib import Path
from typing import Literal

from pydantic import Field, SecretStr, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict
from sqlalchemy import URL

BACKEND_DIR = Path(__file__).resolve().parents[1]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=BACKEND_DIR / ".env", env_file_encoding="utf-8-sig", extra="ignore"
    )

    jwt_secret_key: SecretStr
    jwt_algorithm: Literal["HS256"] = "HS256"
    access_token_expire_minutes: int = Field(default=540, ge=1, le=1440)
    cookie_secure: bool = False
    cors_origins: list[str] = ["http://localhost:5173", "http://127.0.0.1:5173"]

    @field_validator("jwt_secret_key")
    @classmethod
    def validate_secret(cls, value: SecretStr) -> SecretStr:
        if len(value.get_secret_value().encode()) < 32:
            raise ValueError("JWT_SECRET_KEY requiere al menos 32 bytes aleatorios")
        return value

    @field_validator("cors_origins")
    @classmethod
    def validate_origins(cls, value: list[str]) -> list[str]:
        if not value or any(origin == "*" for origin in value):
            raise ValueError("Configura orígenes explícitos")
        return value


class DatabaseSettings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=BACKEND_DIR / ".env",
        env_file_encoding="utf-8-sig",
        extra="ignore",
    )

    db_host: str = "localhost"
    db_port: int = Field(default=5433, ge=1, le=65535)
    db_name: str = "sigfq"
    db_user: str = "sigfq"
    db_password: SecretStr


def database_url() -> URL:
    settings = DatabaseSettings()

    return URL.create(
        drivername="postgresql+psycopg",
        username=settings.db_user,
        password=settings.db_password.get_secret_value(),
        host=settings.db_host,
        port=settings.db_port,
        database=settings.db_name,
    )
