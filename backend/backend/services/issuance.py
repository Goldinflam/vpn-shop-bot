"""Helpers for building the unified ``IssuedVpnOut`` response.

Anything that results in a usable VLESS client — paid purchase, trial,
promo redemption, renewal — should return this shape so the bot can
render a single "connect" UX regardless of the entry point.
"""

from __future__ import annotations

import base64
import io
from urllib.parse import quote

import qrcode
from shared.schemas import IssuedVpnOut, SubscriptionOut

from backend.models import Subscription


def build_happ_import_url(vless_link: str, subscription_url: str | None) -> str:
    """Return a ``happ://...`` deep link for the Happ VPN client.

    Prefers a subscription URL (auto-refreshes when the server rotates
    credentials); falls back to the raw VLESS link otherwise.
    """
    if subscription_url:
        return f"happ://import-sub?url={quote(subscription_url, safe='')}"
    return f"happ://import?url={quote(vless_link, safe='')}"


def render_qr_png_base64(payload: str) -> str:
    """Render ``payload`` as a PNG QR code and return it as base64."""
    img = qrcode.make(payload)
    buf = io.BytesIO()
    img.save(buf)
    return base64.b64encode(buf.getvalue()).decode("ascii")


def issued_vpn_from_subscription(subscription: Subscription) -> IssuedVpnOut:
    """Build an ``IssuedVpnOut`` DTO from a freshly-provisioned subscription."""
    sub_dto = SubscriptionOut.model_validate(subscription)
    qr_payload = subscription.subscription_url or subscription.vless_link
    return IssuedVpnOut(
        subscription=sub_dto,
        vless_link=subscription.vless_link,
        subscription_url=subscription.subscription_url,
        qr_png_base64=render_qr_png_base64(qr_payload),
        happ_import_url=build_happ_import_url(
            subscription.vless_link, subscription.subscription_url
        ),
    )
