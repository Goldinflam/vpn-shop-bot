"""Payment adapter registry keyed by ``PaymentProvider``."""

from __future__ import annotations

from shared.contracts.errors import PaymentError
from shared.enums import PaymentProvider

from backend.config import Settings, get_settings
from backend.payments.base import PaymentProviderAdapter
from backend.payments.cryptobot import CryptoBotAdapter
from backend.payments.test_provider import TestAdapter
from backend.payments.yookassa import YooKassaAdapter


def build_adapter_registry(
    settings: Settings | None = None,
) -> dict[PaymentProvider, PaymentProviderAdapter]:
    """Build default adapters for every supported provider."""
    cfg = settings or get_settings()
    return {
        PaymentProvider.YOOKASSA: YooKassaAdapter(cfg),
        PaymentProvider.CRYPTOBOT: CryptoBotAdapter(cfg),
        PaymentProvider.TEST: TestAdapter(),
    }


def get_adapter(
    provider: PaymentProvider,
    registry: dict[PaymentProvider, PaymentProviderAdapter] | None = None,
) -> PaymentProviderAdapter:
    """Return the adapter for ``provider``, raising if unsupported."""
    effective = registry or build_adapter_registry()
    adapter = effective.get(provider)
    if adapter is None:
        raise PaymentError(f"No adapter configured for provider={provider.value}")
    return adapter
