"""Bot configuration loaded from environment variables."""

from __future__ import annotations

from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict
from shared.enums import Locale


class Settings(BaseSettings):
    """Runtime configuration for the Telegram bot.

    Values are read from environment variables. See ``.env.example`` at the
    repository root for the full list of variables.
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    # --- Telegram ---
    bot_token: SecretStr = Field(..., validation_alias="BOT_TOKEN")

    # --- Backend HTTP API ---
    backend_url: str = Field("http://backend:8000", validation_alias="BACKEND_URL")
    bot_api_token: SecretStr = Field(..., validation_alias="BOT_API_TOKEN")
    admin_api_token: SecretStr | None = Field(default=None, validation_alias="ADMIN_API_TOKEN")
    backend_timeout_s: float = Field(
        default=30.0,
        validation_alias="BACKEND_TIMEOUT_S",
        description="HTTP timeout for bot->backend calls. Must cover slow x-ui login+create.",
    )

    # --- Admin access ---
    bot_admin_ids_raw: str = Field(default="", validation_alias="BOT_ADMIN_IDS")

    # --- i18n ---
    default_locale: Locale = Field(Locale.RU, validation_alias="DEFAULT_LOCALE")

    # --- Misc ---
    log_level: str = Field("INFO", validation_alias="LOG_LEVEL")

    @property
    def admin_ids(self) -> frozenset[int]:
        """Parse comma-separated admin Telegram IDs from ``BOT_ADMIN_IDS``."""
        if not self.bot_admin_ids_raw.strip():
            return frozenset()
        return frozenset(
            int(part.strip()) for part in self.bot_admin_ids_raw.split(",") if part.strip()
        )


def get_settings() -> Settings:
    """Instantiate :class:`Settings` from the current environment."""
    return Settings()
