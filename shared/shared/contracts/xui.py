"""Python contract between `backend` and `xui_client`.

`xui_client` is imported as a library by `backend`. The backend MUST NOT
call `py3xui` directly — it only goes through this protocol.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol, runtime_checkable


@dataclass(frozen=True, slots=True)
class VlessClientResult:
    """Returned by XUIClient.create_vless_client."""

    client_uuid: str
    email: str
    inbound_id: int
    vless_link: str          # vless://...   — full connection URL
    subscription_url: str | None  # x-ui /sub/{id} link if enabled, else None
    qr_png: bytes            # PNG bytes of VLESS link QR code


@dataclass(frozen=True, slots=True)
class TrafficStats:
    email: str
    up_bytes: int
    down_bytes: int
    total_bytes: int
    limit_bytes: int
    enabled: bool
    expiry_time_ms: int      # 0 = no expiry


@dataclass(frozen=True, slots=True)
class InboundSummary:
    id: int
    remark: str
    protocol: str
    port: int
    enabled: bool


@runtime_checkable
class XUIClientProtocol(Protocol):
    """Contract implemented by `xui_client.XUIClient`."""

    async def create_vless_client(
        self,
        *,
        inbound_id: int,
        email: str,
        expire_ts_ms: int,
        traffic_limit_bytes: int,
        telegram_id: int | None = None,
    ) -> VlessClientResult: ...

    async def disable_client(self, *, inbound_id: int, client_uuid: str) -> None: ...

    async def enable_client(self, *, inbound_id: int, client_uuid: str) -> None: ...

    async def delete_client(self, *, inbound_id: int, client_uuid: str) -> None: ...

    async def extend_client(
        self,
        *,
        inbound_id: int,
        client_uuid: str,
        expire_ts_ms: int,
        traffic_limit_bytes: int,
    ) -> None: ...

    async def get_client_traffic(self, *, email: str) -> TrafficStats: ...

    async def reset_client_traffic(self, *, inbound_id: int, email: str) -> None: ...

    async def list_inbounds(self) -> list[InboundSummary]: ...

    async def health_check(self) -> bool: ...
