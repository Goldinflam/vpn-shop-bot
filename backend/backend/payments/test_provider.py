"""Test payment provider — no external calls."""

from __future__ import annotations

import json
import uuid
from collections.abc import Mapping
from typing import TYPE_CHECKING, cast

from shared.contracts.errors import PaymentProviderError
from shared.enums import PaymentStatus

from backend.payments.base import (
    PaymentCreatedResult,
    PaymentProviderAdapter,
    WebhookVerificationResult,
)

if TYPE_CHECKING:
    from backend.models import Payment, Plan, User


class TestAdapter(PaymentProviderAdapter):
    """In-memory provider. Always returns a synthetic pay_url and succeeded webhooks."""

    # Not a pytest test class.
    __test__ = False

    async def create(self, payment: Payment, plan: Plan, user: User) -> PaymentCreatedResult:
        provider_id = f"test-{uuid.uuid4().hex}"
        return PaymentCreatedResult(
            provider_payment_id=provider_id,
            payment_url=f"https://example.test/pay/{provider_id}",
            raw={"provider_payment_id": provider_id, "plan_id": plan.id, "user_id": user.id},
        )

    async def verify_webhook(
        self, body: bytes, headers: Mapping[str, str]
    ) -> WebhookVerificationResult:
        try:
            parsed = json.loads(body.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise PaymentProviderError(f"Invalid TestAdapter webhook body: {exc}") from exc
        if not isinstance(parsed, dict):
            raise PaymentProviderError("TestAdapter webhook body is not an object")

        provider_id = parsed.get("provider_payment_id")
        if not isinstance(provider_id, str) or not provider_id:
            raise PaymentProviderError("TestAdapter webhook missing provider_payment_id")

        status_raw = parsed.get("status", "succeeded")
        try:
            status = PaymentStatus(status_raw if isinstance(status_raw, str) else "succeeded")
        except ValueError as exc:
            raise PaymentProviderError(f"Unknown TestAdapter status: {status_raw}") from exc

        return WebhookVerificationResult(
            provider_payment_id=provider_id,
            status=status,
            raw=cast(dict[str, object], parsed),
        )
