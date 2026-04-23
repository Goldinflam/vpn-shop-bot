from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Any

from pydantic import BaseModel, ConfigDict

from shared.enums import Currency, PaymentProvider, PaymentStatus


class PaymentCreate(BaseModel):
    telegram_id: int
    plan_id: int
    provider: PaymentProvider
    # For renewals — optional existing subscription id
    subscription_id: int | None = None


class PaymentOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: int
    plan_id: int
    subscription_id: int | None = None
    amount: Decimal
    currency: Currency
    provider: PaymentProvider
    provider_payment_id: str | None = None
    payment_url: str | None = None
    status: PaymentStatus
    created_at: datetime


class PaymentWebhook(BaseModel):
    """Generic inbound webhook body; provider-specific parsing is done inside backend."""

    provider: PaymentProvider
    raw: dict[str, Any]
