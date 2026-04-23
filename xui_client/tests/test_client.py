"""Integration-style tests for :class:`xui_client.XUIClient`.

Every network call is intercepted by ``pytest-httpx`` — no live 3x-ui panel
is required. Each test verifies the wire-level contract against the 3x-ui
HTTP surface (endpoints + JSON envelopes).
"""

from __future__ import annotations

import pytest
from shared.contracts.errors import (
    XUIClientNotFoundError,
    XUIError,
    XUIInboundNotFoundError,
)
from shared.contracts.xui import (
    InboundSummary,
    TrafficStats,
    VlessClientResult,
    XUIClientProtocol,
)
from xui_client.testing import ClientFactory, InboundFactory, MockPanel

from xui_client import XUIClient


def test_xui_client_implements_protocol(xui: XUIClient) -> None:
    assert isinstance(xui, XUIClientProtocol)


async def test_list_inbounds(
    xui: XUIClient, panel: MockPanel, make_inbound: InboundFactory
) -> None:
    panel.mock_list_inbounds(
        [make_inbound(inbound_id=1), make_inbound(inbound_id=2, port=8443)]
    )

    inbounds = await xui.list_inbounds()

    assert inbounds == [
        InboundSummary(
            id=1, remark="reality-inbound", protocol="vless", port=443, enabled=True
        ),
        InboundSummary(
            id=2, remark="reality-inbound", protocol="vless", port=8443, enabled=True
        ),
    ]


async def test_health_check_ok(
    xui: XUIClient, panel: MockPanel, make_inbound: InboundFactory
) -> None:
    panel.mock_list_inbounds([make_inbound()])
    assert await xui.health_check() is True


async def test_health_check_failure(xui: XUIClient, panel: MockPanel) -> None:
    panel.mock_status_code(
        method="GET", path="/panel/api/inbounds/list", status=500
    )
    assert await xui.health_check() is False


async def test_create_vless_client_new(
    xui: XUIClient, panel: MockPanel, make_inbound: InboundFactory
) -> None:
    panel.mock_get_inbound(make_inbound(clients=[]))
    panel.mock_add_client()

    result = await xui.create_vless_client(
        inbound_id=1,
        email="ignored@example.com",
        expire_ts_ms=1_700_000_000_000,
        traffic_limit_bytes=10 * 1024**3,
        telegram_id=42,
    )

    assert isinstance(result, VlessClientResult)
    assert result.inbound_id == 1
    assert result.email.startswith("tg_42_")
    assert result.vless_link.startswith(
        f"vless://{result.client_uuid}@vpn.example.com:443?"
    )
    assert "security=reality" in result.vless_link
    assert "pbk=PUBKEY123" in result.vless_link
    assert "sid=abcd1234" in result.vless_link
    assert "sni=www.google.com" in result.vless_link
    assert "fp=chrome" in result.vless_link
    assert result.qr_png.startswith(b"\x89PNG\r\n\x1a\n")
    assert result.subscription_url is None  # no subscription_base_url configured


async def test_create_vless_client_idempotent_by_email(
    xui: XUIClient,
    panel: MockPanel,
    make_inbound: InboundFactory,
    make_client: ClientFactory,
) -> None:
    existing = make_client(
        email="direct@example.com",
        uuid_="22222222-2222-2222-2222-222222222222",
    )
    panel.mock_get_inbound(make_inbound(clients=[existing]))

    result = await xui.create_vless_client(
        inbound_id=1,
        email="direct@example.com",
        expire_ts_ms=0,
        traffic_limit_bytes=0,
        telegram_id=None,
    )

    assert result.client_uuid == "22222222-2222-2222-2222-222222222222"
    assert result.email == "direct@example.com"
    # addClient MUST NOT have been called — pytest-httpx would fail if it
    # received an unmatched request.


async def test_create_vless_client_idempotent_by_telegram_prefix(
    xui: XUIClient,
    panel: MockPanel,
    make_inbound: InboundFactory,
    make_client: ClientFactory,
) -> None:
    existing = make_client(
        email="tg_42_abcd12",
        uuid_="33333333-3333-3333-3333-333333333333",
    )
    panel.mock_get_inbound(make_inbound(clients=[existing]))

    result = await xui.create_vless_client(
        inbound_id=1,
        email="whatever@example.com",
        expire_ts_ms=0,
        traffic_limit_bytes=0,
        telegram_id=42,
    )

    assert result.client_uuid == "33333333-3333-3333-3333-333333333333"
    assert result.email == "tg_42_abcd12"


async def test_create_vless_client_inbound_404(
    xui: XUIClient, panel: MockPanel
) -> None:
    panel.mock_status_code(
        method="GET", path="/panel/api/inbounds/get/99", status=404
    )

    with pytest.raises(XUIInboundNotFoundError):
        await xui.create_vless_client(
            inbound_id=99,
            email="x@y.z",
            expire_ts_ms=0,
            traffic_limit_bytes=0,
        )


async def test_disable_and_enable_client(
    xui: XUIClient,
    panel: MockPanel,
    make_inbound: InboundFactory,
    make_client: ClientFactory,
) -> None:
    uuid_ = "44444444-4444-4444-4444-444444444444"
    client_doc = make_client(
        email="tg_1_xxxxxx",
        uuid_=uuid_,
        enable=True,
    )

    # disable()
    panel.mock_get_inbound(make_inbound(clients=[client_doc]))
    panel.mock_update_client(uuid_)
    await xui.disable_client(inbound_id=1, client_uuid=uuid_)

    # enable()
    client_doc["enable"] = False
    panel.mock_get_inbound(make_inbound(clients=[client_doc]))
    panel.mock_update_client(uuid_)
    await xui.enable_client(inbound_id=1, client_uuid=uuid_)


async def test_delete_client(xui: XUIClient, panel: MockPanel) -> None:
    uuid_ = "55555555-5555-5555-5555-555555555555"
    panel.mock_delete_client(inbound_id=1, client_uuid=uuid_)

    await xui.delete_client(inbound_id=1, client_uuid=uuid_)


async def test_extend_client(
    xui: XUIClient,
    panel: MockPanel,
    make_inbound: InboundFactory,
    make_client: ClientFactory,
) -> None:
    uuid_ = "66666666-6666-6666-6666-666666666666"
    panel.mock_get_inbound(make_inbound(clients=[make_client(uuid_=uuid_)]))
    panel.mock_update_client(uuid_)

    await xui.extend_client(
        inbound_id=1,
        client_uuid=uuid_,
        expire_ts_ms=1_800_000_000_000,
        traffic_limit_bytes=50 * 1024**3,
    )


async def test_extend_client_not_found(
    xui: XUIClient,
    panel: MockPanel,
    make_inbound: InboundFactory,
    make_client: ClientFactory,
) -> None:
    panel.mock_get_inbound(make_inbound(clients=[make_client(uuid_="other")]))
    with pytest.raises(XUIClientNotFoundError):
        await xui.extend_client(
            inbound_id=1,
            client_uuid="does-not-exist",
            expire_ts_ms=0,
            traffic_limit_bytes=0,
        )


async def test_get_client_traffic(
    xui: XUIClient, panel: MockPanel, make_client: ClientFactory
) -> None:
    raw = make_client(
        email="tg_42_abc",
        expiry_time=1_700_000_000_000,
        total_gb=100,
    )
    raw.update({"up": 1500, "down": 3500, "total": 100, "enable": True})
    panel.mock_get_traffic_by_email("tg_42_abc", raw)

    stats = await xui.get_client_traffic(email="tg_42_abc")

    assert stats == TrafficStats(
        email="tg_42_abc",
        up_bytes=1500,
        down_bytes=3500,
        total_bytes=5000,
        limit_bytes=100,
        enabled=True,
        expiry_time_ms=1_700_000_000_000,
    )


async def test_get_client_traffic_not_found(
    xui: XUIClient, panel: MockPanel
) -> None:
    panel.mock_get_traffic_by_email("missing@x.y", None)
    with pytest.raises(XUIClientNotFoundError):
        await xui.get_client_traffic(email="missing@x.y")


async def test_reset_client_traffic(xui: XUIClient, panel: MockPanel) -> None:
    panel.mock_reset_stats(inbound_id=1, email="tg_42_abc")
    await xui.reset_client_traffic(inbound_id=1, email="tg_42_abc")


async def test_auto_relogin_on_401(
    xui: XUIClient, panel: MockPanel, make_inbound: InboundFactory
) -> None:
    # First call → 401, triggers re-login (reusable login mock is already in place),
    # second call → success.
    panel.mock_status_code(
        method="GET", path="/panel/api/inbounds/list", status=401
    )
    panel.mock_list_inbounds([make_inbound()])

    result = await xui.list_inbounds()

    assert len(result) == 1


async def test_panel_error_envelope_raises_xui_error(
    xui: XUIClient, panel: MockPanel
) -> None:
    # 3x-ui returns 200 with {"success": False, ...} — py3xui turns this
    # into a ValueError; the client must normalise it to XUIError.
    panel.httpx_mock.add_response(
        method="POST",
        url=panel.url("/panel/api/inbounds/1/delClient/bad"),
        json={"success": False, "msg": "no such client"},
    )
    with pytest.raises(XUIError):
        await xui.delete_client(inbound_id=1, client_uuid="bad")


async def test_server_error_raises_xui_error(
    xui: XUIClient, panel: MockPanel
) -> None:
    panel.mock_status_code(
        method="GET", path="/panel/api/inbounds/get/1", status=500
    )
    with pytest.raises(XUIError):
        await xui.create_vless_client(
            inbound_id=1,
            email="x@y.z",
            expire_ts_ms=0,
            traffic_limit_bytes=0,
        )
