from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict

from shared.enums import SubscriptionStatus


class SubscriptionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: int
    plan_id: int
    xui_client_uuid: str
    xui_inbound_id: int
    xui_email: str
    vless_link: str
    subscription_url: str | None = None
    traffic_limit_bytes: int
    traffic_used_bytes: int = 0
    starts_at: datetime
    expires_at: datetime
    status: SubscriptionStatus
    created_at: datetime


class SubscriptionRenew(BaseModel):
    plan_id: int


class IssuedVpnOut(BaseModel):
    """Unified response returned by every VPN-issuing endpoint.

    Any action that results in a usable VLESS client — paid purchase, trial
    activation, promo-code redemption, renewal — returns this shape so the
    bot can render the same "connect" UX regardless of the entry point.
    """

    model_config = ConfigDict(from_attributes=True)

    subscription: SubscriptionOut
    vless_link: str
    subscription_url: str | None = None
    qr_png_base64: str
    happ_import_url: str
    """Deep link for the Happ VPN client.

    Format: ``happ://import-sub?url={subscription_url}`` when the panel
    exposes a subscription URL, otherwise ``happ://import?url={vless_link}``.
    """
