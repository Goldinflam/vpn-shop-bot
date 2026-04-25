"""End-to-end API tests."""

from __future__ import annotations

import json
from decimal import Decimal

from backend.models import Plan, User
from httpx import AsyncClient
from shared.contracts.http import (
    ADMIN_PLANS,
    ADMIN_STATS,
    API_PREFIX,
    PAYMENT_GET,
    PAYMENT_WEBHOOK,
    PAYMENTS_CREATE,
    PLAN_GET,
    PLANS_LIST,
    SUBSCRIPTION_GET,
    USER_GET,
    USER_SUBSCRIPTIONS,
    USERS_UPSERT,
)
from shared.enums import PaymentProvider, PaymentStatus
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker


async def test_health_no_auth(client: AsyncClient) -> None:
    resp = await client.get("/health")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}


async def test_users_requires_bot_token(client: AsyncClient) -> None:
    resp = await client.post(
        f"{API_PREFIX}{USERS_UPSERT}",
        json={"telegram_id": 1},
    )
    assert resp.status_code == 401


async def test_users_upsert_and_get(client: AsyncClient, bot_headers: dict[str, str]) -> None:
    payload = {"telegram_id": 7, "username": "a", "language_code": "en"}
    resp = await client.post(f"{API_PREFIX}{USERS_UPSERT}", json=payload, headers=bot_headers)
    assert resp.status_code == 200
    body = resp.json()
    assert body["telegram_id"] == 7
    assert body["locale"] == "en"

    resp = await client.get(f"{API_PREFIX}{USER_GET.format(telegram_id=7)}", headers=bot_headers)
    assert resp.status_code == 200


async def test_user_subscriptions_empty(
    client: AsyncClient,
    bot_headers: dict[str, str],
    sessionmaker: async_sessionmaker[AsyncSession],
) -> None:
    async with sessionmaker() as s:
        s.add(User(telegram_id=9001))
        await s.commit()

    resp = await client.get(
        f"{API_PREFIX}{USER_SUBSCRIPTIONS.format(telegram_id=9001)}",
        headers=bot_headers,
    )
    assert resp.status_code == 200
    assert resp.json() == []


async def test_plans_listing(
    client: AsyncClient,
    bot_headers: dict[str, str],
    sessionmaker: async_sessionmaker[AsyncSession],
) -> None:
    async with sessionmaker() as s:
        s.add_all(
            [
                Plan(name="visible", duration_days=30, traffic_gb=0, price=Decimal("50")),
                Plan(
                    name="hidden",
                    duration_days=30,
                    traffic_gb=0,
                    price=Decimal("50"),
                    is_active=False,
                ),
            ]
        )
        await s.commit()

    resp = await client.get(f"{API_PREFIX}{PLANS_LIST}", headers=bot_headers)
    assert resp.status_code == 200
    names = [p["name"] for p in resp.json()]
    assert "visible" in names
    assert "hidden" not in names


async def test_plan_get_404(client: AsyncClient, bot_headers: dict[str, str]) -> None:
    resp = await client.get(f"{API_PREFIX}{PLAN_GET.format(plan_id=99)}", headers=bot_headers)
    assert resp.status_code == 404


async def test_payment_flow_test_provider(
    client: AsyncClient,
    bot_headers: dict[str, str],
    sessionmaker: async_sessionmaker[AsyncSession],
) -> None:
    async with sessionmaker() as s:
        user = User(telegram_id=500)
        plan = Plan(name="p", duration_days=30, traffic_gb=5, price=Decimal("99"))
        s.add_all([user, plan])
        await s.commit()
        await s.refresh(user)
        await s.refresh(plan)
        plan_id = plan.id

    create_resp = await client.post(
        f"{API_PREFIX}{PAYMENTS_CREATE}",
        json={"telegram_id": 500, "plan_id": plan_id, "provider": PaymentProvider.TEST.value},
        headers=bot_headers,
    )
    assert create_resp.status_code == 200
    body = create_resp.json()
    payment_id = body["id"]
    provider_payment_id = body["provider_payment_id"]
    assert body["status"] == PaymentStatus.PENDING.value

    get_resp = await client.get(
        f"{API_PREFIX}{PAYMENT_GET.format(payment_id=payment_id)}",
        headers=bot_headers,
    )
    assert get_resp.status_code == 200

    webhook_body = json.dumps({"provider_payment_id": provider_payment_id, "status": "succeeded"})
    webhook_resp = await client.post(
        f"{API_PREFIX}{PAYMENT_WEBHOOK.format(provider=PaymentProvider.TEST.value)}",
        content=webhook_body,
        headers={"content-type": "application/json"},
    )
    assert webhook_resp.status_code == 200

    updated = await client.get(
        f"{API_PREFIX}{PAYMENT_GET.format(payment_id=payment_id)}",
        headers=bot_headers,
    )
    data = updated.json()
    assert data["status"] == PaymentStatus.SUCCEEDED.value
    sub_id = data["subscription_id"]
    assert sub_id is not None

    sub_resp = await client.get(
        f"{API_PREFIX}{SUBSCRIPTION_GET.format(subscription_id=sub_id)}",
        headers=bot_headers,
    )
    assert sub_resp.status_code == 200


async def test_admin_requires_admin_token(client: AsyncClient, bot_headers: dict[str, str]) -> None:
    resp = await client.get(f"{API_PREFIX}{ADMIN_STATS}", headers=bot_headers)
    assert resp.status_code == 401


async def test_admin_create_plan(client: AsyncClient, admin_headers: dict[str, str]) -> None:
    resp = await client.post(
        f"{API_PREFIX}{ADMIN_PLANS}",
        json={"name": "admin-made", "duration_days": 7, "traffic_gb": 1, "price": "19.00"},
        headers=admin_headers,
    )
    assert resp.status_code == 201
    body = resp.json()
    assert body["name"] == "admin-made"


async def test_admin_stats(client: AsyncClient, admin_headers: dict[str, str]) -> None:
    resp = await client.get(f"{API_PREFIX}{ADMIN_STATS}", headers=admin_headers)
    assert resp.status_code == 200
    body = resp.json()
    assert "users_total" in body
    assert "revenue_succeeded" in body
