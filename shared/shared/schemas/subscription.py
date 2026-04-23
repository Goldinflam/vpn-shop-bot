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
    traffic_limit_bytes: int
    traffic_used_bytes: int = 0
    starts_at: datetime
    expires_at: datetime
    status: SubscriptionStatus
    created_at: datetime


class SubscriptionRenew(BaseModel):
    plan_id: int
