"""High-level asynchronous client around ``py3xui``.

:class:`XUIClient` implements :class:`shared.contracts.xui.XUIClientProtocol`
and is the single entry point used by the backend. It owns:

* session lifecycle (login, transparent re-login on 401),
* idempotent VLESS client creation (dedupe by email or ``tg_{id}_*`` prefix),
* VLESS link + QR generation,
* normalisation of all panel errors into
  :mod:`shared.contracts.errors` ``XUIError`` subclasses.
"""

from __future__ import annotations

import asyncio
import json
import logging
import secrets
import uuid
from collections.abc import Awaitable, Callable
from typing import Any, TypeVar
from urllib.parse import urljoin

import httpx
from py3xui import AsyncApi, Client, Inbound
from shared.contracts.errors import (
    XUIAuthError,
    XUIClientNotFoundError,
    XUIError,
    XUIInboundNotFoundError,
)
from shared.contracts.xui import InboundSummary, TrafficStats, VlessClientResult

from xui_client.qr import qr_png
from xui_client.retries import retry_on_auth
from xui_client.vless import build_vless_link, public_host_from_url

logger = logging.getLogger(__name__)

T = TypeVar("T")

_DEFAULT_TIMEOUT_S: float = 10.0
_RANDOM_SUFFIX_BYTES = 3  # 6 hex chars


class XUIClient:
    """Domain wrapper around :class:`py3xui.AsyncApi`.

    Arguments:
        host: Base URL of the 3x-ui panel (e.g. ``https://panel.example.com``).
        username: Panel login.
        password: Panel password.
        tls_verify: Verify the panel's TLS certificate (default ``True``).
        default_inbound_id: Inbound used when no ``inbound_id`` is passed.
        timeout: Per-request timeout in seconds (default ``10``).
        public_host: Hostname embedded in VLESS URLs. Defaults to the
            hostname parsed from *host*.
        subscription_base_url: If the panel exposes a subscription endpoint
            (``subJson``/``subPath``), pass its base here to get non-``None``
            ``subscription_url`` values in :meth:`create_vless_client`.
    """

    def __init__(
        self,
        *,
        host: str,
        username: str,
        password: str,
        tls_verify: bool = True,
        default_inbound_id: int | None = None,
        timeout: float = _DEFAULT_TIMEOUT_S,
        public_host: str | None = None,
        subscription_base_url: str | None = None,
    ) -> None:
        self._api = AsyncApi(
            host=host,
            username=username,
            password=password,
            use_tls_verify=tls_verify,
            logger=logger,
        )
        # Disable py3xui's internal network retries — we own the retry policy.
        self._api.client.max_retries = 1
        self._api.inbound.max_retries = 1
        self._api.database.max_retries = 1
        self._api.server.max_retries = 1

        self._host = host.rstrip("/")
        self._default_inbound_id = default_inbound_id
        self._timeout = timeout
        self._public_host = public_host or public_host_from_url(host)
        self._subscription_base_url = (
            subscription_base_url.rstrip("/") if subscription_base_url else None
        )
        self._login_lock = asyncio.Lock()
        self._started = False

    # ------------------------------------------------------------------ lifecycle

    async def start(self) -> None:
        """Authenticate against the panel. Call once before other methods."""
        await self._login()
        self._started = True

    async def close(self) -> None:
        """Dispose of cached state. ``py3xui`` creates a fresh ``httpx`` client
        per request, so nothing to tear down — this is a placeholder for
        future connection-pool support and symmetry with :meth:`start`.
        """
        self._started = False

    async def __aenter__(self) -> XUIClient:
        await self.start()
        return self

    async def __aexit__(self, *_exc: object) -> None:
        await self.close()

    async def _login(self) -> None:
        async with self._login_lock:
            try:
                await asyncio.wait_for(self._api.login(), timeout=self._timeout)
            except (httpx.HTTPStatusError, httpx.RequestError, ValueError) as exc:
                raise XUIAuthError(f"Login failed: {exc}") from exc
            except TimeoutError as exc:
                raise XUIAuthError("Login timed out") from exc

    # ------------------------------------------------------------------ helpers

    async def _call(self, action: Callable[[], Awaitable[T]]) -> T:
        """Run *action* with per-call timeout, error mapping, and auto re-login."""

        async def guarded() -> T:
            try:
                return await asyncio.wait_for(action(), timeout=self._timeout)
            except httpx.HTTPStatusError as exc:
                status = exc.response.status_code
                if status == 401:
                    raise XUIAuthError("Session expired") from exc
                if status == 404:
                    raise XUIClientNotFoundError(str(exc)) from exc
                raise XUIError(f"HTTP {status}: {exc}") from exc
            except TimeoutError as exc:
                raise XUIError(f"Request timed out after {self._timeout}s") from exc
            except httpx.RequestError as exc:
                raise XUIError(f"Network error: {exc}") from exc
            except ValueError as exc:
                # py3xui raises ValueError when the panel returns success=false.
                raise XUIError(str(exc)) from exc

        return await retry_on_auth(guarded, self._login)

    async def _get_inbound(self, inbound_id: int) -> Inbound:
        try:
            return await self._call(lambda: self._api.inbound.get_by_id(inbound_id))
        except XUIError as exc:
            if isinstance(exc, XUIClientNotFoundError):
                raise XUIInboundNotFoundError(
                    f"Inbound {inbound_id} not found"
                ) from exc
            raise

    async def _get_client_in_inbound(
        self, *, inbound_id: int, client_uuid: str
    ) -> tuple[Inbound, Client]:
        inbound = await self._get_inbound(inbound_id)
        clients = _clients_of(inbound)
        for client in clients:
            if str(client.id) == str(client_uuid):
                return inbound, client
        raise XUIClientNotFoundError(
            f"Client {client_uuid} not found in inbound {inbound_id}"
        )

    @staticmethod
    def _normalise_email(email: str, telegram_id: int | None) -> str:
        if telegram_id is None:
            return email
        return f"tg_{telegram_id}_{secrets.token_hex(_RANDOM_SUFFIX_BYTES)}"

    @staticmethod
    def _find_existing(
        inbound: Inbound, *, email: str, telegram_id: int | None
    ) -> Client | None:
        clients = _clients_of(inbound)
        if telegram_id is not None:
            prefix = f"tg_{telegram_id}_"
            for client in clients:
                if client.email.startswith(prefix):
                    return client
            return None
        for client in clients:
            if client.email == email:
                return client
        return None

    def _subscription_url(self, sub_id: str | None) -> str | None:
        if not self._subscription_base_url or not sub_id:
            return None
        return f"{self._subscription_base_url}/{sub_id}"

    # ------------------------------------------------------------------ API

    async def create_vless_client(
        self,
        *,
        inbound_id: int,
        email: str,
        expire_ts_ms: int,
        traffic_limit_bytes: int,
        telegram_id: int | None = None,
    ) -> VlessClientResult:
        """Create a VLESS client, idempotently.

        If a matching client already exists (same email, or — when
        *telegram_id* is given — any ``tg_{telegram_id}_*`` email) the
        existing record is returned untouched and a warning is logged.
        """
        inbound = await self._get_inbound(inbound_id)

        existing = self._find_existing(
            inbound, email=email, telegram_id=telegram_id
        )
        if existing is not None:
            logger.warning(
                "VLESS client already exists in inbound %s: %s",
                inbound_id,
                existing.email,
            )
            return self._build_result(inbound, existing)

        client_email = self._normalise_email(email, telegram_id)
        client_uuid = str(uuid.uuid4())
        sub_id = secrets.token_hex(8)
        flow = _default_flow_for(inbound)

        new_client = Client(
            id=client_uuid,
            email=client_email,
            enable=True,
            expiry_time=expire_ts_ms,
            total_gb=traffic_limit_bytes,
            flow=flow,
            sub_id=sub_id,
            limit_ip=0,
            tg_id=str(telegram_id) if telegram_id is not None else "",
        )

        await self._call(
            lambda: self._api.client.add(inbound_id, [new_client])
        )

        new_client.inbound_id = inbound_id
        return self._build_result(inbound, new_client)

    async def disable_client(
        self, *, inbound_id: int, client_uuid: str
    ) -> None:
        """Disable a client in the given inbound (without deleting it)."""
        _inbound, client = await self._get_client_in_inbound(
            inbound_id=inbound_id, client_uuid=client_uuid
        )
        client.enable = False
        client.inbound_id = inbound_id
        await self._call(lambda: self._api.client.update(client_uuid, client))

    async def enable_client(
        self, *, inbound_id: int, client_uuid: str
    ) -> None:
        """Re-enable a previously disabled client."""
        _inbound, client = await self._get_client_in_inbound(
            inbound_id=inbound_id, client_uuid=client_uuid
        )
        client.enable = True
        client.inbound_id = inbound_id
        await self._call(lambda: self._api.client.update(client_uuid, client))

    async def delete_client(
        self, *, inbound_id: int, client_uuid: str
    ) -> None:
        """Permanently remove a client from the inbound."""
        await self._call(
            lambda: self._api.client.delete(inbound_id, client_uuid)
        )

    async def extend_client(
        self,
        *,
        inbound_id: int,
        client_uuid: str,
        expire_ts_ms: int,
        traffic_limit_bytes: int,
    ) -> None:
        """Update expiry and traffic limit for an existing client."""
        _inbound, client = await self._get_client_in_inbound(
            inbound_id=inbound_id, client_uuid=client_uuid
        )
        client.expiry_time = expire_ts_ms
        client.total_gb = traffic_limit_bytes
        client.inbound_id = inbound_id
        await self._call(lambda: self._api.client.update(client_uuid, client))

    async def get_client_traffic(self, *, email: str) -> TrafficStats:
        """Return traffic statistics for the client identified by *email*."""
        client = await self._call(lambda: self._api.client.get_by_email(email))
        if client is None:
            raise XUIClientNotFoundError(
                f"Client with email {email!r} not found"
            )
        return TrafficStats(
            email=client.email,
            up_bytes=int(client.up or 0),
            down_bytes=int(client.down or 0),
            total_bytes=int((client.up or 0) + (client.down or 0)),
            limit_bytes=int(client.total or 0),
            enabled=bool(client.enable),
            expiry_time_ms=int(client.expiry_time or 0),
        )

    async def reset_client_traffic(
        self, *, inbound_id: int, email: str
    ) -> None:
        """Reset the cumulative traffic counters for a client."""
        await self._call(
            lambda: self._api.client.reset_stats(inbound_id, email)
        )

    async def list_inbounds(self) -> list[InboundSummary]:
        """Return a lightweight summary of every inbound on the panel."""
        inbounds = await self._call(lambda: self._api.inbound.get_list())
        return [
            InboundSummary(
                id=int(ib.id),
                remark=ib.remark or "",
                protocol=ib.protocol,
                port=int(ib.port),
                enabled=bool(ib.enable),
            )
            for ib in inbounds
        ]

    async def health_check(self) -> bool:
        """Return ``True`` if the panel responds to an authenticated call.

        Implemented as a lightweight inbound list call — we don't care about
        the returned data, only that the panel accepts our session.
        """
        try:
            await self._call(lambda: self._api.inbound.get_list())
        except XUIError:
            return False
        return True

    # ------------------------------------------------------------------ internals

    def _build_result(
        self, inbound: Inbound, client: Client
    ) -> VlessClientResult:
        remark = client.email or (inbound.remark or f"inbound-{inbound.id}")
        vless_link = build_vless_link(
            inbound=inbound,
            client_uuid=str(client.id),
            public_host=self._public_host,
            remark=remark,
            client_flow=client.flow or None,
        )
        qr_bytes = qr_png(vless_link)
        return VlessClientResult(
            client_uuid=str(client.id),
            email=client.email,
            inbound_id=int(inbound.id),
            vless_link=vless_link,
            subscription_url=self._subscription_url(client.sub_id),
            qr_png=qr_bytes,
        )

    # URL helper retained for potential future extensions (e.g. panel sub settings).
    def _panel_url(self, path: str) -> str:
        return urljoin(self._host + "/", path.lstrip("/"))


def _clients_of(inbound: Inbound) -> list[Client]:
    settings = inbound.settings
    if settings is None:
        return []
    # py3xui parses settings JSON into a Settings model with a ``clients`` list.
    clients: Any = getattr(settings, "clients", None)
    if isinstance(clients, list):
        return [c for c in clients if isinstance(c, Client)]
    if isinstance(settings, str):
        try:
            data = json.loads(settings)
        except json.JSONDecodeError:
            return []
        raw = data.get("clients", []) if isinstance(data, dict) else []
        return [Client.model_validate(c) for c in raw]
    return []


def _default_flow_for(inbound: Inbound) -> str:
    """Pick a sensible default ``flow`` for a new VLESS client."""
    stream = inbound.stream_settings
    security: str | None = None
    if hasattr(stream, "security"):
        security = getattr(stream, "security", None)
    elif isinstance(stream, str) and stream:
        try:
            security = json.loads(stream).get("security")
        except json.JSONDecodeError:
            security = None
    if security == "reality":
        return "xtls-rprx-vision"
    return ""
