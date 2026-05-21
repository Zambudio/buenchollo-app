"""Application settings loaded from environment variables."""

from functools import lru_cache

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Runtime configuration for the API and external integrations."""

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_name: str = "BuenChollo API"
    app_env: str = "local"
    log_level: str = "INFO"

    # Orígenes CORS permitidos, separados por comas en la variable de entorno.
    # Ejemplo: CORS_ORIGINS=https://buenchollotech.com,https://www.buenchollotech.com
    # En local se puede dejar vacío o usar "*" para permitir cualquier origen.
    cors_origins: list[str] = Field(default=["*"])

    @field_validator("cors_origins", mode="before")
    @classmethod
    def parse_cors_origins(cls, v: str | list) -> list[str]:
        if isinstance(v, str):
            return [origin.strip() for origin in v.split(",") if origin.strip()]
        return v

    amazon_client_id: str = ""
    amazon_client_secret: str = ""
    amazon_affiliate_tag: str = "buenchollo0b-21"
    amazon_api_version: str = "3.2"
    amazon_credential_version: str = ""
    amazon_marketplace: str = "www.amazon.es"
    amazon_auth_endpoint: str = "https://api.amazon.co.uk/auth/o2/token"
    amazon_oauth_scope: str = "creatorsapi::default"
    amazon_supported_credential_versions: tuple[str, ...] = Field(default=("3.2", "3.1", "3.3"))

    openai_api_key: str = ""
    openai_model: str = "gpt-4o"

    supabase_url: str = ""
    supabase_key: str = ""
    database_url: str = ""

    @property
    def amazon_effective_credential_version(self) -> str:
        """Return the configured Amazon credential version, accepting the legacy env name."""
        return self.amazon_credential_version or self.amazon_api_version


@lru_cache
def get_settings() -> Settings:
    """Return cached settings so dependencies share the same config."""
    return Settings()
