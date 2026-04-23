"""Unit tests for :mod:`xui_client.vless`.

The VLESS URL builder is pure — it doesn't touch the network — so we can
feed it hand-crafted ``py3xui.Inbound`` fixtures and assert on every
segment of the resulting URL.
"""

from __future__ import annotations

import json
from typing import Any
from urllib.parse import parse_qs, unquote, urlparse

from py3xui import Inbound
from xui_client.vless import build_vless_link, public_host_from_url


def _inbound_from(settings_stream: dict[str, Any], *, port: int = 443) -> Inbound:
    payload = {
        "id": 1,
        "enable": True,
        "port": port,
        "protocol": "vless",
        "remark": "r",
        "listen": "",
        "settings": json.dumps({"clients": [], "decryption": "none", "fallbacks": []}),
        "streamSettings": json.dumps(settings_stream),
        "sniffing": json.dumps({"enabled": True}),
    }
    return Inbound.model_validate(payload)


def test_public_host_from_url() -> None:
    assert public_host_from_url("https://panel.example.com:2053/path") == "panel.example.com"
    assert public_host_from_url("http://1.2.3.4") == "1.2.3.4"


def test_build_reality_link_has_all_expected_params() -> None:
    stream = {
        "network": "tcp",
        "security": "reality",
        "realitySettings": {
            "serverNames": ["www.google.com"],
            "publicKey": "PUBKEY",
            "shortIds": ["short1", "short2"],
            "fingerprint": "chrome",
            "settings": {
                "publicKey": "PUBKEY",
                "fingerprint": "chrome",
                "spiderX": "/",
            },
        },
        "tcpSettings": {"header": {"type": "none"}},
    }
    inbound = _inbound_from(stream)

    url = build_vless_link(
        inbound=inbound,
        client_uuid="abc-uuid",
        public_host="vpn.example.com",
        remark="my client",
        client_flow="xtls-rprx-vision",
    )

    parsed = urlparse(url)
    assert parsed.scheme == "vless"
    assert parsed.username == "abc-uuid"
    assert parsed.hostname == "vpn.example.com"
    assert parsed.port == 443
    assert unquote(parsed.fragment) == "my client"

    qs = parse_qs(parsed.query)
    assert qs["type"] == ["tcp"]
    assert qs["security"] == ["reality"]
    assert qs["pbk"] == ["PUBKEY"]
    assert qs["sid"] == ["short1"]
    assert qs["sni"] == ["www.google.com"]
    assert qs["fp"] == ["chrome"]
    assert qs["spx"] == ["/"]
    assert qs["flow"] == ["xtls-rprx-vision"]


def test_build_tls_ws_link_has_expected_params() -> None:
    stream = {
        "network": "ws",
        "security": "tls",
        "tlsSettings": {
            "serverName": "tls.example.com",
            "alpn": ["h2", "http/1.1"],
            "settings": {"fingerprint": "firefox", "allowInsecure": True},
        },
        "wsSettings": {"path": "/ws", "headers": {"Host": "tls.example.com"}},
    }
    inbound = _inbound_from(stream, port=8443)

    url = build_vless_link(
        inbound=inbound,
        client_uuid="uuid-2",
        public_host="tls.example.com",
        remark="tls-client",
    )

    parsed = urlparse(url)
    qs = parse_qs(parsed.query)
    assert parsed.port == 8443
    assert qs["type"] == ["ws"]
    assert qs["security"] == ["tls"]
    assert qs["sni"] == ["tls.example.com"]
    assert qs["fp"] == ["firefox"]
    assert qs["alpn"] == ["h2,http/1.1"]
    assert qs["allowInsecure"] == ["1"]
    # No flow requested → must not appear.
    assert "flow" not in qs


def test_build_link_with_grpc_and_none_security() -> None:
    stream = {
        "network": "grpc",
        "security": "none",
        "grpcSettings": {"serviceName": "svc", "multiMode": True},
    }
    inbound = _inbound_from(stream)
    url = build_vless_link(
        inbound=inbound,
        client_uuid="uuid-3",
        public_host="vpn.example.com",
        remark="grpc",
    )
    qs = parse_qs(urlparse(url).query)
    assert qs["type"] == ["grpc"]
    assert qs["security"] == ["none"]
