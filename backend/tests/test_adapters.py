"""Tests for payment provider adapters (isolated, no network)."""

from __future__ import annotations

import hashlib
import hmac
import json
from decimal import Decimal

import pytest
from backend.config import Settings
from backend.models import Payment, Plan, User
from backend.payments.cryptobot import CryptoBotAdapter, _compute_signature
from backend.payments.test_provider import TestAdapter
from backend.payments.yookassa import YooKassaAdapter
from shared.contracts.errors import PaymentProviderError
from shared.enums import Currency, PaymentProvider, PaymentStatus


def _payment() -> Payment:
    p = Payment(
        user_id=1,
        plan_id=1,
        amount=Decimal("150.00"),
        currency=Currency.RUB,
        provider=PaymentProvider.YOOKASSA,
        status=PaymentStatus.PENDING,
        raw_payload={},
    )
    p.id = 42
    return p


def _plan() -> Plan:
    plan = Plan(name="p", duration_days=30, traffic_gb=0, price=Decimal("150.00"))
    plan.id = 7
    return plan


def _user() -> User:
    u = User(telegram_id=123, username="u")
    u.id = 11
    return u


async def test_yookassa_create_uses_injected_callable() -> None:
    def fake_sdk(body: dict[str, object], idem_key: str) -> dict[str, object]:
        assert isinstance(idem_key, str) and len(idem_key) > 0
        return {
            "id": "yk-1",
            "confirmation": {"type": "redirect", "confirmation_url": "https://pay.example/x"},
            "status": "pending",
        }

    adapter = YooKassaAdapter(Settings(), sdk_create=fake_sdk)
    result = await adapter.create(_payment(), _plan(), _user())
    assert result.provider_payment_id == "yk-1"
    assert result.payment_url == "https://pay.example/x"


async def test_yookassa_webhook_parses_status() -> None:
    adapter = YooKassaAdapter(Settings())
    body = json.dumps(
        {"event": "payment.succeeded", "object": {"id": "yk-2", "status": "succeeded"}}
    ).encode()
    out = await adapter.verify_webhook(body, {})
    assert out.provider_payment_id == "yk-2"
    assert out.status == PaymentStatus.SUCCEEDED


async def test_yookassa_webhook_invalid_body() -> None:
    adapter = YooKassaAdapter(Settings())
    with pytest.raises(PaymentProviderError):
        await adapter.verify_webhook(b"not-json", {})


async def test_cryptobot_create_and_webhook_signature() -> None:
    async def fake_invoice(body: dict[str, object]) -> dict[str, object]:
        return {"invoice_id": "cb-1", "pay_url": "https://cryptobot/pay/1"}

    settings = Settings(cryptobot_token="secret-token")
    adapter = CryptoBotAdapter(settings, invoice_create=fake_invoice)
    result = await adapter.create(_payment(), _plan(), _user())
    assert result.provider_payment_id == "cb-1"
    assert result.payment_url == "https://cryptobot/pay/1"

    body = json.dumps({"payload": {"invoice_id": "cb-1", "status": "paid"}}).encode()
    sig = _compute_signature("secret-token", body)
    out = await adapter.verify_webhook(body, {"crypto-pay-api-signature": sig})
    assert out.status == PaymentStatus.SUCCEEDED

    with pytest.raises(PaymentProviderError):
        await adapter.verify_webhook(body, {"crypto-pay-api-signature": "bad"})


async def test_cryptobot_webhook_signature_matches_library_hmac() -> None:
    token = "my-token"
    expected = hmac.new(
        hashlib.sha256(token.encode()).digest(),
        b"payload",
        hashlib.sha256,
    ).hexdigest()
    assert _compute_signature(token, b"payload") == expected


async def test_test_adapter_roundtrip() -> None:
    adapter = TestAdapter()
    created = await adapter.create(_payment(), _plan(), _user())
    body = json.dumps(
        {"provider_payment_id": created.provider_payment_id, "status": "succeeded"}
    ).encode()
    verified = await adapter.verify_webhook(body, {})
    assert verified.status == PaymentStatus.SUCCEEDED
    assert verified.provider_payment_id == created.provider_payment_id
