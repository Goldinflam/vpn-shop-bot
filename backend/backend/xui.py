"""XUIClient integration.

Backend MUST NOT import ``py3xui`` directly. Use the protocol contract from
``shared.contracts.xui`` and the concrete implementation re-exported from
``xui_client``. The factory defers the real import so tests can freely mock
the client via ``unittest.mock.AsyncMock(spec=XUIClientProtocol)``.
"""

from __future__ import annotations

from typing import cast

from shared.contracts.xui import XUIClientProtocol

from backend.config import Settings, get_settings

_client: XUIClientProtocol | None = None


def build_xui_client(settings: Settings | None = None) -> XUIClientProtocol:
    """Create a concrete XUI client instance.

    The heavy ``xui_client`` dependency is imported lazily to keep test
    startup cheap and to allow this module to load even before the
    sibling package is fully implemented.
    """
    cfg = settings or get_settings()
    import xui_client as xui_client_module

    factory = xui_client_module.XUIClient
    client = factory(
        host=cfg.xui_host,
        username=cfg.xui_username,
        password=cfg.xui_password,
        verify_tls=cfg.xui_use_tls_verify,
    )
    return cast(XUIClientProtocol, client)


def get_xui_client() -> XUIClientProtocol:
    """Return the process-wide XUI client."""
    global _client
    if _client is None:
        _client = build_xui_client()
    return _client


def set_xui_client(client: XUIClientProtocol) -> None:
    """Override the XUI client (used by tests / lifespan)."""
    global _client
    _client = client
