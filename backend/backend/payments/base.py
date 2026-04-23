"""Protocol + dataclasses shared by all payment provider adapters."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import TYPE_CHECKING, Protocol, runtime_checkable

from shared.enums import PaymentStatus

if TYPE_CHECKING:
    from backend.models import Payment, Plan, User


@dataclass(frozen=True, slots=True)
class PaymentCreatedResult:
    """Result returned by ``PaymentProviderAdapter.create``."""

    provider_payment_id: str
    payment_url: str | None
    raw: dict[str, object]


@dataclass(frozen=True, slots=True)
class WebhookVerificationResult:
    """Result of webhook signature + payload verification."""

    provider_payment_id: str
    status: PaymentStatus
    raw: dict[str, object]


@runtime_checkable
class PaymentProviderAdapter(Protocol):
    """Contract implemented by every payment provider adapter."""

    async def create(
        self, payment: Payment, plan: Plan, user: User
    ) -> PaymentCreatedResult: ...

    async def verify_webhook(
        self, body: bytes, headers: Mapping[str, str]
    ) -> WebhookVerificationResult: ...
