"""Pydantic DTOs used across module boundaries.

Never import SQLAlchemy models into this package. These schemas are the
wire format for the HTTP API and for inter-module Python calls.
"""

from shared.schemas.payment import PaymentCreate, PaymentOut, PaymentWebhook
from shared.schemas.plan import PlanCreate, PlanOut, PlanUpdate
from shared.schemas.promo import (
    PromoApplyIn,
    PromoApplyOut,
    PromoCodeOut,
    TrialCreateIn,
)
from shared.schemas.subscription import (
    IssuedVpnOut,
    SubscriptionOut,
    SubscriptionRenew,
)
from shared.schemas.user import UserOut, UserUpsert

__all__ = [
    "IssuedVpnOut",
    "PaymentCreate",
    "PaymentOut",
    "PaymentWebhook",
    "PlanCreate",
    "PlanOut",
    "PlanUpdate",
    "PromoApplyIn",
    "PromoApplyOut",
    "PromoCodeOut",
    "SubscriptionOut",
    "SubscriptionRenew",
    "TrialCreateIn",
    "UserOut",
    "UserUpsert",
]
