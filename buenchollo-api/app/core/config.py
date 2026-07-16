"""Application settings loaded from environment variables."""

import json
from functools import lru_cache
from typing import Annotated

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict


class Settings(BaseSettings):
    """Runtime configuration for the API and external integrations."""

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_name: str = "BuenChollo API"
    app_env: str = "local"
    log_level: str = "INFO"
    # "json" (structured, una línea por log — recomendado para producción/Docker)
    # o "text" (formato legible — recomendado para desarrollo local).
    log_format: str = "json"

    # Rate limiting (slowapi). Desactivable con RATE_LIMIT_ENABLED=false
    # cuando se quieran bombardear endpoints en tests sin disparar 429.
    rate_limit_enabled: bool = True

    # Scheduler de mantenimiento de deals dentro del proceso web. Poner a
    # false cuando el scheduler corra en un proceso dedicado
    # (`python -m app.run_scheduler`) — imprescindible antes de subir
    # uvicorn a --workers N, o los jobs se ejecutarían N veces (M-07).
    scheduler_enabled: bool = True

    # Sentry (error tracking). Si SENTRY_DSN está vacío, el SDK no se
    # inicializa y todo funciona normal: útil en local y en tests.
    sentry_dsn: str = ""
    # Etiqueta del entorno enviada con cada evento. Si no se define
    # explícitamente, hereda app_env (local/staging/production).
    sentry_environment: str = ""
    # Sample rate de "transactions" (performance monitoring). 0.0 = sólo
    # errores, sin traces. Subir si se quiere medir latencias. Cobra
    # cuota en el plan free de Sentry, así que dejamos 0 por defecto.
    sentry_traces_sample_rate: float = 0.0
    # Versión de la app para tagging — útil para correlacionar bugs con
    # despliegues concretos. Vacío => no se manda.
    sentry_release: str = ""

    # Orígenes CORS permitidos, separados por comas en la variable de entorno.
    # Ejemplo: CORS_ORIGINS=https://buenchollotech.com,https://www.buenchollotech.com
    # En local se puede dejar vacío o usar "*" para permitir cualquier origen.
    cors_origins: Annotated[list[str], NoDecode] = Field(default=["*"])

    @field_validator("cors_origins", mode="before")
    @classmethod
    def parse_cors_origins(cls, v: str | list) -> list[str]:
        # Acepta ambos formatos en la variable de entorno: JSON array
        # ('["a.com","b.com"]', formato histórico de los .env desplegados)
        # y CSV plano ('a.com,b.com'). Sin esto, un .env en formato JSON
        # se parsearía como CSV crudo dejando corchetes/comillas en los
        # orígenes ('["a.com"'), que nunca casarían con un Origin real.
        if isinstance(v, str):
            s = v.strip()
            if s.startswith("["):
                try:
                    parsed = json.loads(s)
                    if isinstance(parsed, list):
                        return [str(o).strip() for o in parsed if str(o).strip()]
                except json.JSONDecodeError:
                    pass  # no era JSON válido: se intenta como CSV
            return [origin.strip() for origin in s.split(",") if origin.strip()]
        return v

    @property
    def effective_cors_origins(self) -> list[str]:
        origins = list(dict.fromkeys(self.cors_origins))
        if self.app_env == "production" and "*" not in origins:
            origins.extend(
                origin
                for origin in (
                    "https://buenchollotech.com",
                    "https://www.buenchollotech.com",
                )
                if origin not in origins
            )
        if self.app_env != "production" and "*" not in origins:
            origins.extend(
                origin
                for origin in (
                    "http://localhost:8080",
                    "http://127.0.0.1:8080",
                    "http://localhost:8081",
                    "http://127.0.0.1:8081",
                    "http://localhost:8082",
                    "http://127.0.0.1:8082",
                    "http://localhost:5173",
                    "http://127.0.0.1:5173",
                )
                if origin not in origins
            )
        return origins

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
    # Secreto HS256 legacy de Supabase Auth. Solo necesario si el proyecto
    # firmara los JWT con HS256; con claves asimétricas (ES256/RS256, el caso
    # actual) la verificación usa el JWKS público y esto puede quedar vacío.
    supabase_jwt_secret: str = ""
    database_url: str = ""

    telegram_bot_token: str = ""
    telegram_main_channel_id: str = ""
    telegram_admin_channel_id: str = ""

    @property
    def amazon_effective_credential_version(self) -> str:
        """Return the configured Amazon credential version, accepting the legacy env name."""
        return self.amazon_credential_version or self.amazon_api_version


@lru_cache
def get_settings() -> Settings:
    """Return cached settings so dependencies share the same config."""
    return Settings()
