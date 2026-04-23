from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field

from shared.enums import Locale


class UserUpsert(BaseModel):
    """Used by the bot to register/refresh a Telegram user in backend."""

    telegram_id: int = Field(..., gt=0)
    username: str | None = None
    first_name: str | None = None
    last_name: str | None = None
    language_code: str | None = None


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    telegram_id: int
    username: str | None
    first_name: str | None
    last_name: str | None
    locale: Locale = Locale.RU
    balance: Decimal = Decimal("0")
    is_admin: bool = False
    is_banned: bool = False
    created_at: datetime
