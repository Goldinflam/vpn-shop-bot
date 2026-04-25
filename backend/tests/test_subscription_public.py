"""Public ``GET /sub/{sub_token}`` endpoint."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest
from backend.models import (
    Plan,
    Server,
    Subscription,
    SubscriptionClient,
    User,
)
from httpx import AsyncClient
from shared.contracts.http import SUB_PUBLIC
from shared.enums import Currency, SubscriptionStatus
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker


async def _seed_subscription(
    sessionmaker: async_sessionmaker[AsyncSession],
    server: Server,
    *,
    sub_token: str = "tok-abc",
    status: SubscriptionStatus = SubscriptionStatus.ACTIVE,
    enabled: bool = True,
) -> Subscription:
    async with sessionmaker() as s:
        user = User(telegram_id=42, username="u")
        plan = Plan(
            name="any",
            duration_days=30,
            traffic_gb=50,
            price=Decimal("100"),
            currency=Currency.RUB,
        )
        s.add_all([user, plan])
        await s.flush()
        sub = Subscription(
            user_id=user.id,
            plan_id=plan.id,
            sub_token=sub_token,
            xui_client_uuid="u",
            xui_inbound_id=server.inbound_id,
            xui_email="e",
            vless_link="vless://primary",
            traffic_limit_bytes=0,
            traffic_used_bytes=0,
            starts_at=datetime.now(UTC),
            expires_at=datetime.now(UTC) + timedelta(days=30),
            status=status,
        )
        s.add(sub)
        await s.flush()
        s.add(
            SubscriptionClient(
                subscription_id=sub.id,
                server_id=server.id,
                xui_inbound_id=server.inbound_id,
                xui_client_uuid="cu1",
                xui_email="e1",
                vless_link="vless://server-1",
                enabled=enabled,
            )
        )
        await s.commit()
        await s.refresh(sub)
        return sub


async def test_sub_returns_plain_text_links(
    client: AsyncClient,
    sessionmaker: async_sessionmaker[AsyncSession],
    server_row: Server,
) -> None:
    await _seed_subscription(sessionmaker, server_row, sub_token="tok-ok")
    resp = await client.get(SUB_PUBLIC.format(sub_token="tok-ok"))
    assert resp.status_code == 200
    assert resp.headers["content-type"].startswith("text/plain")
    body = resp.text
    assert body.strip().splitlines() == ["vless://server-1"]


async def test_sub_unknown_token_404(client: AsyncClient) -> None:
    resp = await client.get(SUB_PUBLIC.format(sub_token="does-not-exist"))
    assert resp.status_code == 404
    assert resp.json()["detail"] == "subscription_not_found"


async def test_sub_expired_subscription_404(
    client: AsyncClient,
    sessionmaker: async_sessionmaker[AsyncSession],
    server_row: Server,
) -> None:
    await _seed_subscription(
        sessionmaker,
        server_row,
        sub_token="tok-exp",
        status=SubscriptionStatus.EXPIRED,
    )
    resp = await client.get(SUB_PUBLIC.format(sub_token="tok-exp"))
    assert resp.status_code == 404
    assert resp.json()["detail"] == "subscription_not_active"


async def test_sub_filters_disabled_clients(
    client: AsyncClient,
    sessionmaker: async_sessionmaker[AsyncSession],
    server_row: Server,
) -> None:
    await _seed_subscription(sessionmaker, server_row, sub_token="tok-disabled", enabled=False)
    resp = await client.get(SUB_PUBLIC.format(sub_token="tok-disabled"))
    assert resp.status_code == 404
    assert resp.json()["detail"] == "subscription_not_active"


@pytest.mark.parametrize("disabled_server", [True])
async def test_sub_filters_disabled_server(
    client: AsyncClient,
    sessionmaker: async_sessionmaker[AsyncSession],
    server_row: Server,
    disabled_server: bool,
) -> None:
    await _seed_subscription(sessionmaker, server_row, sub_token="tok-srv-off")
    if disabled_server:
        async with sessionmaker() as s:
            srv = await s.get(Server, server_row.id)
            assert srv is not None
            srv.enabled = False
            await s.commit()
    resp = await client.get(SUB_PUBLIC.format(sub_token="tok-srv-off"))
    assert resp.status_code == 404
