"""CryptoBot (@CryptoBot via aiocryptopay) payment provider adapter."""

from __future__ import annotations

import hashlib
import hmac
import json
from collections.abc import Awaitable, Callable, Mapping
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
    "active": PaymentStatus.PENDING,
    "paid": PaymentStatus.SUCCEEDED,
    "expired": PaymentStatus.FAILED,
}


InvoiceCreator = Callable[[dict[str, object]], Awaitable[dict[str, object]]]


class CryptoBotAdapter(PaymentProviderAdapter):
    """Adapter over ``aiocryptopay``.

    Real network access is wrapped behind ``_invoice_create`` so tests can
    inject a stub without the SDK being present.
    """

    def __init__(
        self,
        settings: Settings | None = None,
        *,
        invoice_create: InvoiceCreator | None = None,
    ) -> None:
        self._settings = settings or get_settings()
        self._invoice_create = invoice_create

    async def create(self, payment: Payment, plan: Plan, user: User) -> PaymentCreatedResult:
        body: dict[str, object] = {
            "asset": payment.currency.value,
            "amount": f"{payment.amount:.2f}",
            "description": f"{plan.name} (telegram_id={user.telegram_id})",
            "payload": json.dumps({"internal_payment_id": payment.id}),
            "allow_anonymous": False,
        }

        raw = await self._run_invoice_create(body)

        provider_id = _as_str(raw.get("invoice_id")) or _as_str(raw.get("hash"))
        if not provider_id:
            raise PaymentProviderError("CryptoBot response missing invoice id")

        payment_url = _as_str(raw.get("pay_url")) or _as_str(raw.get("bot_invoice_url"))

        return PaymentCreatedResult(
            provider_payment_id=provider_id,
            payment_url=payment_url,
            raw=raw,
        )

    async def verify_webhook(
        self, body: bytes, headers: Mapping[str, str]
    ) -> WebhookVerificationResult:
        signature = headers.get("crypto-pay-api-signature") or headers.get(
            "Crypto-Pay-Api-Signature"
        )
        if signature and self._settings.cryptobot_token:
            expected = _compute_signature(self._settings.cryptobot_token, body)
            if not hmac.compare_digest(expected, signature):
                raise PaymentProviderError("CryptoBot webhook signature mismatch")

        try:
            parsed = json.loads(body.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise PaymentProviderError(f"Invalid CryptoBot webhook body: {exc}") from exc
        if not isinstance(parsed, dict):
            raise PaymentProviderError("CryptoBot webhook body is not an object")

        payload = parsed.get("payload")
        if not isinstance(payload, dict):
            raise PaymentProviderError("CryptoBot webhook missing 'payload'")

        provider_id = _as_str(payload.get("invoice_id")) or _as_str(payload.get("hash"))
        if not provider_id:
            raise PaymentProviderError("CryptoBot webhook missing invoice id")

        status_raw = _as_str(payload.get("status")) or ""
        status = _STATUS_MAP.get(status_raw, PaymentStatus.FAILED)

        return WebhookVerificationResult(
            provider_payment_id=provider_id,
            status=status,
            raw=cast(dict[str, object], parsed),
        )

    async def _run_invoice_create(self, body: dict[str, object]) -> dict[str, object]:
        if self._invoice_create is not None:
            return await self._invoice_create(body)
        return await self._default_invoice_create(body)

    async def _default_invoice_create(
        self, body: dict[str, object]
    ) -> dict[str, object]:  # pragma: no cover - network path
        try:
            from aiocryptopay import AioCryptoPay
        except ImportError as exc:
            raise PaymentProviderError("aiocryptopay not installed") from exc

        network = self._settings.cryptobot_network
        client = AioCryptoPay(token=self._settings.cryptobot_token, network=network)
        try:
            invoice = await client.create_invoice(**body)
        except Exception as exc:
            raise PaymentProviderError(f"CryptoBot SDK call failed: {exc}") from exc
        finally:
            await client.close()

        dumped = invoice.model_dump()
        if isinstance(dumped, dict):
            return cast(dict[str, object], dumped)
        return {}


def _compute_signature(token: str, body: bytes) -> str:
    """Compute the ``Crypto-Pay-Api-Signature`` HMAC as per CryptoBot docs."""
    secret = hashlib.sha256(token.encode("utf-8")).digest()
    return hmac.new(secret, body, hashlib.sha256).hexdigest()


def _as_str(value: object) -> str | None:
    if isinstance(value, str) and value:
        return value
    if isinstance(value, int):
        return str(value)
    return None
