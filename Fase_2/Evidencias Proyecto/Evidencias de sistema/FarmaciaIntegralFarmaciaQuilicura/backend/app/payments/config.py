"""Configuración privada de Mercado Pago para E7-H2."""

from urllib.parse import urlsplit

from pydantic import SecretStr, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

from app.config import BACKEND_DIR
from app.payments.preference import public_https_url


class PaymentSettings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=BACKEND_DIR / ".env",
        env_file_encoding="utf-8-sig",
        env_prefix="MP_",
        extra="ignore",
        hide_input_in_errors=True,
    )

    access_token: SecretStr
    webhook_secret: SecretStr | None = None
    public_base_url: str | None = None
    checkout_enabled: bool = False

    @field_validator("access_token")
    @classmethod
    def validate_access_token(cls, value: SecretStr) -> SecretStr:
        token = value.get_secret_value().strip()
        if not token or token == "PEGA_AQUI_TU_ACCESS_TOKEN_DE_PRUEBA":
            raise ValueError("Configura MP_ACCESS_TOKEN en backend/.env.")
        return SecretStr(token)

    @field_validator("webhook_secret")
    @classmethod
    def validate_webhook_secret(cls, value: SecretStr | None) -> SecretStr | None:
        if value is None:
            return None
        secret = value.get_secret_value().strip()
        if not secret or secret == "PEGA_AQUI_LA_CLAVE_SECRETA":
            raise ValueError("Configura MP_WEBHOOK_SECRET en backend/.env.")
        return SecretStr(secret)

    @field_validator("public_base_url")
    @classmethod
    def validate_public_base_url(cls, value: str | None) -> str | None:
        if value is None:
            return None
        value = public_https_url(value.strip()).rstrip("/")
        parsed = urlsplit(value)
        if parsed.path or parsed.query:
            raise ValueError("MP_PUBLIC_BASE_URL debe ser el origen HTTPS sin ruta.")
        return value


class PaymentWorkerSettings(BaseSettings):
    """Permite arrancar la API sin credenciales mientras el proceso esté apagado."""

    model_config = PaymentSettings.model_config
    expiration_enabled: bool = False
