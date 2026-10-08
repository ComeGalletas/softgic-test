from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Runtime configuration, read from environment variables (and `.env` if present)."""

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    crm_url: str = Field(default="http://localhost:9000", alias="CRM_URL")
    crm_max_intentos: int = Field(default=3, ge=1, alias="CRM_MAX_INTENTOS")
    crm_timeout_segundos: float = Field(default=2.0, gt=0, alias="CRM_TIMEOUT_SEGUNDOS")
    crm_backoff_base: float = Field(default=0.5, ge=0, alias="CRM_BACKOFF_BASE")

    database_url: str = Field(default="sqlite:///./solicitudes.db", alias="DATABASE_URL")

    openai_api_key: str | None = Field(default=None, alias="OPENAI_API_KEY")
    openai_model: str = Field(default="gpt-4o-mini", alias="OPENAI_MODEL")

    precio_input_por_millon: float = Field(default=0.15, ge=0, alias="PRECIO_INPUT_POR_MILLON")
    precio_output_por_millon: float = Field(default=0.60, ge=0, alias="PRECIO_OUTPUT_POR_MILLON")


@lru_cache
def get_settings() -> Settings:
    return Settings()
