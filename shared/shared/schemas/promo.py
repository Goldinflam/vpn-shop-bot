from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field

from shared.schemas.subscription import IssuedVpnOut


class PromoCodeOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    code: str
    is_trial: bool
    discount_percent: int | None = None
    trial_days: int | None = None
    trial_traffic_gb: int | None = None
    usage_limit: int | None = None
    used_count: int = 0
    per_user_limit: int = 1
    valid_from: datetime | None = None
    valid_until: datetime | None = None
    is_active: bool = True


class PromoApplyIn(BaseModel):
    telegram_id: int
    code: str = Field(..., min_length=1, max_length=64)


class PromoApplyOut(BaseModel):
    """Result of ``POST /promo/apply``.

    Either ``issued`` is filled (trial / free-days promo) OR ``discount_percent``
    is filled (reduces price on the next paid purchase). Never both.
    """

    model_config = ConfigDict(from_attributes=True)

    code: str
    is_trial: bool
    issued: IssuedVpnOut | None = None
    discount_percent: int | None = None
    discount_amount: Decimal | None = None


class TrialCreateIn(BaseModel):
    telegram_id: int
