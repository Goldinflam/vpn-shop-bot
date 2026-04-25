"""XUIClient integration.

Backend MUST NOT import ``py3xui`` directly. Use the protocol contract from
``shared.contracts.xui`` and the concrete implementation re-exported from
``xui_client``. The factory defers the real import so tests can freely mock
the client via ``unittest.mock.AsyncMock(spec=XUIClientProtocol)``.
"""

from __future__ import annotations

import logging
from typing import cast

from shared.contracts.xui import XUIClientProtocol

from backend.config import Settings, get_settings

logger = logging.getLogger(__name__)

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
        tls_verify=cfg.xui_use_tls_verify,
        default_inbound_id=cfg.xui_inbound_id,
        subscription_base_url=cfg.xui_sub_base_url or None,
    )
    return cast(XUIClientProtocol, client)


async def start_xui_client(client: XUIClientProtocol) -> None:
    """Authenticate the panel session during app startup.

    3x-ui's API requires an explicit ``login()`` call before any request;
    without this the first call fails with:
        "Before making a POST request, you must use the login() method."
    """
    start = getattr(client, "start", None)
    if start is None:
        return
    try:
        await start()
    except Exception:  # noqa: BLE001 — keep app startup resilient
        logger.exception("XUI panel login failed; requests will retry on demand")


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
