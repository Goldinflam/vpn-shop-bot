"""Pool of :class:`XUIClient` instances, keyed by ``Server.id``.

The single-server prototype kept one client in module state. With multi-server
support we need a per-server client (different host/credentials/inbound) but
still want lazy login + transparent re-login on 401.

The pool is created at app startup and refreshed (cheaply) every time a
subscription is provisioned: new ``servers`` rows or edits to existing rows
are picked up without restarting the process.
"""

from __future__ import annotations

import asyncio
import logging
from collections.abc import Callable
from typing import cast

from shared.contracts.xui import XUIClientProtocol
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.models import Server

logger = logging.getLogger(__name__)


def _build_client(server: Server) -> XUIClientProtocol:
    import xui_client as xui_client_module

    factory = xui_client_module.XUIClient
    client = factory(
        host=server.host,
        username=server.username,
        password=server.password,
        tls_verify=server.tls_verify,
        default_inbound_id=server.inbound_id,
        public_host=server.public_host or None,
        subscription_base_url=server.subscription_base_url or None,
    )
    return cast(XUIClientProtocol, client)


class XUIPool:
    """Holds one :class:`XUIClient` per :class:`Server` row.

    Thread/coroutine-safe via an internal lock. Clients are constructed on
    demand and started lazily.
    """

    def __init__(
        self,
        builder: Callable[[Server], XUIClientProtocol] = _build_client,
    ) -> None:
        self._builder = builder
        self._clients: dict[int, XUIClientProtocol] = {}
        self._fingerprints: dict[int, tuple[str, str, int, bool]] = {}
        self._lock = asyncio.Lock()

    @staticmethod
    def _fingerprint(server: Server) -> tuple[str, str, int, bool]:
        return (server.host, server.username, server.inbound_id, server.tls_verify)

    async def get(self, server: Server) -> XUIClientProtocol:
        """Return a started client for *server*. Rebuilds if fingerprint changed."""
        async with self._lock:
            existing = self._clients.get(server.id)
            fp = self._fingerprint(server)
            if existing is None or self._fingerprints.get(server.id) != fp:
                client = self._builder(server)
                start = getattr(client, "start", None)
                if start is not None:
                    try:
                        await start()
                    except Exception:  # noqa: BLE001 — keep pool resilient
                        logger.exception(
                            "x-ui login failed for server %s (%s); subsequent calls will retry",
                            server.name,
                            server.host,
                        )
                self._clients[server.id] = client
                self._fingerprints[server.id] = fp
            return self._clients[server.id]

    async def remove(self, server_id: int) -> None:
        async with self._lock:
            client = self._clients.pop(server_id, None)
            self._fingerprints.pop(server_id, None)
        if client is not None:
            close = getattr(client, "close", None)
            if close is not None:
                try:
                    await close()
                except Exception:  # noqa: BLE001
                    logger.exception("x-ui close failed for server_id=%s", server_id)


async def list_enabled_servers(session: AsyncSession) -> list[Server]:
    """Return all ``enabled=True`` servers ordered by id (creation order)."""
    result = await session.execute(
        select(Server).where(Server.enabled.is_(True)).order_by(Server.id)
    )
    return list(result.scalars().all())


_pool: XUIPool | None = None


def get_xui_pool() -> XUIPool:
    """Return the process-wide :class:`XUIPool`."""
    global _pool
    if _pool is None:
        _pool = XUIPool()
    return _pool


def set_xui_pool(pool: XUIPool) -> None:
    """Override the pool (used by tests / lifespan)."""
    global _pool
    _pool = pool
