"""Application configuration loaded from environment via pydantic-settings."""

from __future__ import annotations

from functools import lru_cache
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Backend runtime configuration."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    # --- general ---
    environment: Literal["dev", "prod", "test"] = "dev"
    log_level: str = "INFO"

    # --- server ---
    backend_host: str = "0.0.0.0"  # noqa: S104 — intentional bind for docker
    backend_port: int = 8000

    # --- database ---
    database_url: str = "sqlite+aiosqlite:///./dev.db"

    # --- auth ---
    bot_api_token: str = "change-me-bot-to-backend-shared-secret"  # noqa: S105
    admin_api_token: str = "change-me-admin-secret"  # noqa: S105

    # --- 3x-ui (legacy single-server fallback; PRIMARY config now lives in
    #             the ``servers`` table, see ``backend/services/servers.py``) ---
    xui_host: str = "https://your-panel.example.com"
    xui_username: str = "admin"
    xui_password: str = "admin"  # noqa: S105
    xui_inbound_id: int = 1
    xui_use_tls_verify: bool = True
    xui_sub_base_url: str = ""

    # --- public subscription URL ---
    public_sub_base_url: str = Field(
        default="",
        description=(
            "Public base URL for the merged ``GET /sub/{sub_token}`` endpoint. "
            "Example: ``http://1.2.3.4:8000``. Used to build "
            "``IssuedVpnOut.subscription_url`` for the bot."
        ),
    )

    # --- trial defaults ---
    trial_duration_hours: int = Field(default=24, ge=1)
    trial_traffic_gb: int = Field(default=10, ge=0)

    # --- YooKassa ---
    yookassa_shop_id: str = ""
    yookassa_secret_key: str = ""
    yookassa_return_url: str = "https://t.me/your_bot"

    # --- CryptoBot ---
    cryptobot_token: str = ""
    cryptobot_network: Literal["mainnet", "testnet"] = "mainnet"

    # --- scheduler ---
    expire_cron_minutes: int = Field(
        default=5, description="APScheduler interval for subscription expiration check"
    )


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Cached settings accessor."""
    return Settings()
