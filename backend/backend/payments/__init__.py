"""Payment provider adapters."""

from backend.payments.base import (
    PaymentCreatedResult,
    PaymentProviderAdapter,
    WebhookVerificationResult,
)
from backend.payments.cryptobot import CryptoBotAdapter
from backend.payments.factory import build_adapter_registry, get_adapter
from backend.payments.test_provider import TestAdapter
from backend.payments.yookassa import YooKassaAdapter

__all__ = [
    "CryptoBotAdapter",
    "PaymentCreatedResult",
    "PaymentProviderAdapter",
    "TestAdapter",
    "WebhookVerificationResult",
    "YooKassaAdapter",
    "build_adapter_registry",
    "get_adapter",
]
