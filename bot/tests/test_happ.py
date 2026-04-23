"""Tests for bot.utils.happ — deep-link UX used by trial / promo / buy flows."""

from __future__ import annotations

import base64
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock

import pytest
from bot.i18n import I18n
from bot.utils.happ import HAPP_DOWNLOAD_URL, happ_buttons, send_issued_vpn
from shared.enums import Locale, SubscriptionStatus
from shared.schemas import IssuedVpnOut, SubscriptionOut


def _issued(subscription_url: str | None = "https://panel.example.com/sub/abc") -> IssuedVpnOut:
    sub = SubscriptionOut(
        id=1,
        user_id=1,
        plan_id=1,
        xui_client_uuid="u",
        xui_inbound_id=1,
        xui_email="tg1",
        vless_link="vless://uuid@example.com:443?type=tcp#plan",
        subscription_url=subscription_url,
        traffic_limit_bytes=0,
        traffic_used_bytes=0,
        starts_at=datetime(2024, 1, 1),
        expires_at=datetime(2024, 2, 1),
        status=SubscriptionStatus.ACTIVE,
        created_at=datetime(2024, 1, 1),
    )
    qr_b64 = base64.b64encode(b"\x89PNG\r\n\x1a\nfake-png").decode("ascii")
    happ = (
        f"happ://import-sub?url={subscription_url}"
        if subscription_url
        else "happ://import?url=vless%3A%2F%2Fuuid%40example.com%3A443%3Ftype%3Dtcp%23plan"
    )
    return IssuedVpnOut(
        subscription=sub,
        vless_link=sub.vless_link,
        subscription_url=subscription_url,
        qr_png_base64=qr_b64,
        happ_import_url=happ,
    )


def _t():
    return I18n(default_locale=Locale.RU).translator(Locale.RU)


def test_happ_buttons_includes_connect_and_download() -> None:
    kb = happ_buttons(_issued(), _t())
    urls = [btn.url for row in kb.inline_keyboard for btn in row]
    assert any(url and url.startswith("happ://") for url in urls)
    assert HAPP_DOWNLOAD_URL in urls


def test_happ_buttons_skips_open_subscription_when_missing() -> None:
    kb = happ_buttons(_issued(subscription_url=None), _t())
    texts = [btn.text for row in kb.inline_keyboard for btn in row]
    assert "🔄 Открыть подписку" not in texts


@pytest.mark.asyncio
async def test_send_issued_vpn_sends_text_and_photo() -> None:
    issued = _issued()
    message = MagicMock()
    message.answer = AsyncMock()
    message.answer_photo = AsyncMock()

    await send_issued_vpn(message, issued, _t())

    assert message.answer.call_count == 1
    assert message.answer_photo.call_count == 1
    sent_text = message.answer.call_args.args[0]
    assert issued.vless_link in sent_text
    kb = message.answer.call_args.kwargs["reply_markup"]
    urls = [btn.url for row in kb.inline_keyboard for btn in row]
    assert any(u and u.startswith("happ://import-sub?url=") for u in urls)
