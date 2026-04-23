"""Shared fixtures for xui_client tests.

All network calls are intercepted by ``pytest-httpx`` — no live 3x-ui panel
is required.
"""

from __future__ import annotations

import json
from collections.abc import AsyncIterator, Iterator

import pytest
import pytest_asyncio
from pytest_httpx import HTTPXMock
from xui_client.testing import (
    ClientDict,
    ClientFactory,
    InboundDict,
    InboundFactory,
    MockPanel,
    StreamDict,
)

from xui_client import XUIClient

PANEL_BASE = "https://panel.example.com"
DEFAULT_INBOUND_ID = 1


@pytest.fixture
def panel_base() -> str:
    return PANEL_BASE


@pytest.fixture
def panel(httpx_mock: HTTPXMock) -> Iterator[MockPanel]:
    yield MockPanel(base=PANEL_BASE, httpx_mock=httpx_mock)


@pytest_asyncio.fixture
async def xui(panel: MockPanel) -> AsyncIterator[XUIClient]:
    panel.mock_login()
    client = XUIClient(
        host=PANEL_BASE,
        username="admin",
        password="admin",
        default_inbound_id=DEFAULT_INBOUND_ID,
        timeout=5.0,
        public_host="vpn.example.com",
    )
    await client.start()
    try:
        yield client
    finally:
        await client.close()


@pytest.fixture
def reality_stream() -> StreamDict:
    return {
        "network": "tcp",
        "security": "reality",
        "externalProxy": [],
        "realitySettings": {
            "show": False,
            "xver": 0,
            "dest": "www.google.com:443",
            "serverNames": ["www.google.com", "google.com"],
            "privateKey": "PRIVATE",
            "publicKey": "PUBKEY123",
            "shortIds": ["abcd1234", "deadbeef"],
            "fingerprint": "chrome",
            "settings": {
                "publicKey": "PUBKEY123",
                "fingerprint": "chrome",
                "spiderX": "/",
            },
        },
        "tcpSettings": {"header": {"type": "none"}},
    }


@pytest.fixture
def tls_stream() -> StreamDict:
    return {
        "network": "ws",
        "security": "tls",
        "externalProxy": [],
        "tlsSettings": {
            "serverName": "vpn.example.com",
            "alpn": ["h2", "http/1.1"],
            "settings": {"fingerprint": "firefox", "allowInsecure": False},
        },
        "wsSettings": {"path": "/ws", "headers": {"Host": "vpn.example.com"}},
    }


def _inbound_fixture(
    *,
    inbound_id: int,
    port: int,
    remark: str,
    stream: StreamDict,
    clients: list[ClientDict],
) -> InboundDict:
    settings = {"clients": clients, "decryption": "none", "fallbacks": []}
    return {
        "id": inbound_id,
        "enable": True,
        "port": port,
        "protocol": "vless",
        "remark": remark,
        "listen": "",
        "tag": f"inbound-{port}",
        "up": 0,
        "down": 0,
        "total": 0,
        "expiryTime": 0,
        "clientStats": [],
        "settings": json.dumps(settings),
        "streamSettings": json.dumps(stream),
        "sniffing": json.dumps(
            {"enabled": True, "destOverride": ["http", "tls"]}
        ),
    }


@pytest.fixture
def make_inbound(reality_stream: StreamDict) -> InboundFactory:
    def _factory(
        *,
        inbound_id: int = DEFAULT_INBOUND_ID,
        port: int = 443,
        remark: str = "reality-inbound",
        stream: StreamDict | None = None,
        clients: list[ClientDict] | None = None,
    ) -> InboundDict:
        return _inbound_fixture(
            inbound_id=inbound_id,
            port=port,
            remark=remark,
            stream=stream if stream is not None else reality_stream,
            clients=clients if clients is not None else [],
        )

    return _factory


@pytest.fixture
def make_client() -> ClientFactory:
    def _factory(
        *,
        email: str = "tg_42_abc123",
        uuid_: str = "11111111-1111-1111-1111-111111111111",
        enable: bool = True,
        expiry_time: int = 0,
        total_gb: int = 0,
        sub_id: str = "sub42",
        flow: str = "xtls-rprx-vision",
        tg_id: str | int = "",
    ) -> ClientDict:
        return {
            "id": uuid_,
            "email": email,
            "enable": enable,
            "expiryTime": expiry_time,
            "totalGB": total_gb,
            "total": total_gb,
            "subId": sub_id,
            "flow": flow,
            "tgId": tg_id,
            "limitIp": 0,
            "up": 0,
            "down": 0,
        }

    return _factory
