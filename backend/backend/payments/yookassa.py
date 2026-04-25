"""YooKassa payment provider adapter."""

from __future__ import annotations

import json
import uuid
from collections.abc import Callable, Mapping
from typing import TYPE_CHECKING, cast

from shared.contracts.errors import PaymentProviderError
from shared.enums import PaymentStatus

from backend.config import Settings, get_settings
from backend.payments.base import (
    PaymentCreatedResult,
    PaymentProviderAdapter,
    WebhookVerificationResult,
)

if TYPE_CHECKING:
    from backend.models import Payment, Plan, User


_STATUS_MAP: dict[str, PaymentStatus] = {
    "succeeded": PaymentStatus.SUCCEEDED,
    "canceled": PaymentStatus.CANCELED,
    "waiting_for_capture": PaymentStatus.PENDING,
    "pending": PaymentStatus.PENDING,
}


class YooKassaAdapter(PaymentProviderAdapter):
    """Adapter over the ``yookassa`` SDK.

    The SDK is imported lazily so that tests can replace ``_sdk_create``
    without installing/using the real SDK. Tests may also pass a
    ``sdk_create`` callable to the constructor for full isolation.
    """

    def __init__(
        self,
        settings: Settings | None = None,
        *,
        sdk_create: Callable[[dict[str, object], str], dict[str, object]] | None = None,
    ) -> None:
        self._settings = settings or get_settings()
        self._sdk_create = sdk_create

    async def create(self, payment: Payment, plan: Plan, user: User) -> PaymentCreatedResult:
        idem_key = uuid.uuid4().hex
        request_body = {
            "amount": {"value": f"{payment.amount:.2f}", "currency": payment.currency.value},
            "confirmation": {
                "type": "redirect",
                "return_url": self._settings.yookassa_return_url,
            },
            "capture": True,
            "description": f"{plan.name} (telegram_id={user.telegram_id})",
            "metadata": {
                "internal_payment_id": str(payment.id),
                "telegram_id": str(user.telegram_id),
                "plan_id": str(plan.id),
            },
        }

        raw = await self._call_create(request_body, idem_key)

        provider_id = _as_str(raw.get("id"))
        if not provider_id:
            raise PaymentProviderError("YooKassa response missing 'id'")

        confirmation = raw.get("confirmation")
        payment_url: str | None = None
        if isinstance(confirmation, dict):
            value = confirmation.get("confirmation_url")
            payment_url = _as_str(value)

        return PaymentCreatedResult(
            provider_payment_id=provider_id,
            payment_url=payment_url,
            raw=raw,
        )

    async def verify_webhook(
        self, body: bytes, headers: Mapping[str, str]
    ) -> WebhookVerificationResult:
        # YooKassa webhooks are authenticated primarily by IP whitelist and
        # optional basic auth. Here we parse the JSON body; production
        # deployments should enforce IP allow-listing at the reverse proxy.
        try:
            parsed = json.loads(body.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise PaymentProviderError(f"Invalid YooKassa webhook body: {exc}") from exc
        if not isinstance(parsed, dict):
            raise PaymentProviderError("YooKassa webhook body is not an object")

        obj = parsed.get("object")
        if not isinstance(obj, dict):
            raise PaymentProviderError("YooKassa webhook body missing 'object'")

        provider_id = _as_str(obj.get("id"))
        if not provider_id:
            raise PaymentProviderError("YooKassa webhook missing payment id")

        status_raw = _as_str(obj.get("status")) or ""
        status = _STATUS_MAP.get(status_raw, PaymentStatus.FAILED)

        return WebhookVerificationResult(
            provider_payment_id=provider_id,
            status=status,
            raw=cast(dict[str, object], parsed),
        )

    async def _call_create(self, body: dict[str, object], idem_key: str) -> dict[str, object]:
        if self._sdk_create is not None:
            result = self._sdk_create(body, idem_key)
        else:
            result = self._default_sdk_create(body, idem_key)
        if not isinstance(result, dict):
            raise PaymentProviderError("YooKassa SDK returned non-dict response")
        return result

    def _default_sdk_create(
        self, body: dict[str, object], idem_key: str
    ) -> dict[str, object]:  # pragma: no cover - network path
        try:
            from yookassa import Configuration
            from yookassa import Payment as SDKPayment
        except ImportError as exc:
            raise PaymentProviderError("yookassa SDK not installed") from exc

        Configuration.account_id = self._settings.yookassa_shop_id
        Configuration.secret_key = self._settings.yookassa_secret_key
        try:
            sdk_payment = SDKPayment.create(body, idem_key)
        except Exception as exc:
            raise PaymentProviderError(f"YooKassa SDK call failed: {exc}") from exc
        raw = vars(sdk_payment) if hasattr(sdk_payment, "__dict__") else {}
        if isinstance(raw, dict):
            return cast(dict[str, object], dict(raw))
        return {}


def _as_str(value: object) -> str | None:
    """Return ``str`` if ``value`` is a non-empty string, else ``None``."""
    if isinstance(value, str) and value:
        return value
    return None
