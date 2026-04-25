"""API tests for /trial/create and /promo/apply."""

from __future__ import annotations

from decimal import Decimal

import pytest
from backend.models import PromoCode
from httpx import AsyncClient
from shared.contracts.http import API_PREFIX, PROMO_APPLY, TRIAL_CREATE
from shared.enums import Currency, PaymentProvider
from shared.schemas import PaymentCreate, PaymentOut, UserOut, UserUpsert
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker


async def _upsert_user(
    client: AsyncClient, headers: dict[str, str], telegram_id: int = 9001
) -> UserOut:
    dto = UserUpsert(telegram_id=telegram_id, username="promo_user")
    resp = await client.post(f"{API_PREFIX}/users", json=dto.model_dump(), headers=headers)
    resp.raise_for_status()
    return UserOut.model_validate(resp.json())


async def test_trial_create_requires_bot_token(client: AsyncClient) -> None:
    resp = await client.post(f"{API_PREFIX}{TRIAL_CREATE}", json={"telegram_id": 1})
    assert resp.status_code == 401


async def test_trial_create_happy_path(client: AsyncClient, bot_headers: dict[str, str]) -> None:
    await _upsert_user(client, bot_headers, telegram_id=9101)
    resp = await client.post(
        f"{API_PREFIX}{TRIAL_CREATE}",
        json={"telegram_id": 9101},
        headers=bot_headers,
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["vless_link"].startswith("vless://")
    assert body["happ_import_url"].startswith("happ://")
    assert body["qr_png_base64"]
    assert body["subscription"]["status"] == "active"


async def test_trial_create_twice_conflicts(
    client: AsyncClient, bot_headers: dict[str, str]
) -> None:
    await _upsert_user(client, bot_headers, telegram_id=9102)
    r1 = await client.post(
        f"{API_PREFIX}{TRIAL_CREATE}",
        json={"telegram_id": 9102},
        headers=bot_headers,
    )
    assert r1.status_code == 200
    r2 = await client.post(
        f"{API_PREFIX}{TRIAL_CREATE}",
        json={"telegram_id": 9102},
        headers=bot_headers,
    )
    assert r2.status_code == 409
    assert r2.json()["code"] == "trial_already_claimed"


async def test_promo_apply_unknown(client: AsyncClient, bot_headers: dict[str, str]) -> None:
    await _upsert_user(client, bot_headers, telegram_id=9103)
    resp = await client.post(
        f"{API_PREFIX}{PROMO_APPLY}",
        json={"telegram_id": 9103, "code": "NOPE"},
        headers=bot_headers,
    )
    assert resp.status_code == 404
    assert resp.json()["code"] == "promo_not_found"


async def test_promo_apply_trial_code_issues_vpn(
    client: AsyncClient,
    bot_headers: dict[str, str],
    sessionmaker: async_sessionmaker[AsyncSession],
) -> None:
    await _upsert_user(client, bot_headers, telegram_id=9104)
    async with sessionmaker() as s:
        s.add(
            PromoCode(
                code="FREE7",
                is_trial=True,
                trial_days=7,
                trial_traffic_gb=10,
                per_user_limit=1,
            )
        )
        await s.commit()

    resp = await client.post(
        f"{API_PREFIX}{PROMO_APPLY}",
        json={"telegram_id": 9104, "code": "FREE7"},
        headers=bot_headers,
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["is_trial"] is True
    assert body["issued"]["vless_link"].startswith("vless://")
    assert body["issued"]["happ_import_url"].startswith("happ://")


async def test_promo_apply_discount_code(
    client: AsyncClient,
    bot_headers: dict[str, str],
    sessionmaker: async_sessionmaker[AsyncSession],
) -> None:
    await _upsert_user(client, bot_headers, telegram_id=9105)
    async with sessionmaker() as s:
        s.add(
            PromoCode(
                code="SAVE15",
                is_trial=False,
                discount_percent=15,
                per_user_limit=1,
            )
        )
        await s.commit()
    resp = await client.post(
        f"{API_PREFIX}{PROMO_APPLY}",
        json={"telegram_id": 9105, "code": "SAVE15"},
        headers=bot_headers,
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["is_trial"] is False
    assert body["discount_percent"] == 15
    assert body["issued"] is None


async def test_promo_apply_reuse_blocked(
    client: AsyncClient,
    bot_headers: dict[str, str],
    sessionmaker: async_sessionmaker[AsyncSession],
) -> None:
    await _upsert_user(client, bot_headers, telegram_id=9106)
    async with sessionmaker() as s:
        s.add(
            PromoCode(
                code="ONCE",
                is_trial=False,
                discount_percent=10,
                per_user_limit=1,
            )
        )
        await s.commit()

    payload = {"telegram_id": 9106, "code": "ONCE"}
    r1 = await client.post(f"{API_PREFIX}{PROMO_APPLY}", json=payload, headers=bot_headers)
    assert r1.status_code == 200
    r2 = await client.post(f"{API_PREFIX}{PROMO_APPLY}", json=payload, headers=bot_headers)
    assert r2.status_code == 409
    assert r2.json()["code"] == "promo_already_used"


async def test_subscription_issued_endpoint(
    client: AsyncClient,
    bot_headers: dict[str, str],
    sessionmaker: async_sessionmaker[AsyncSession],
) -> None:
    """After a paid purchase completes, /subscriptions/{id}/issued returns IssuedVpnOut."""
    # Seed a paid plan and run the full payment flow against the test provider.
    user = await _upsert_user(client, bot_headers, telegram_id=9107)

    from backend.models import Plan

    async with sessionmaker() as s:
        plan = Plan(
            name="30d",
            description="paid",
            duration_days=30,
            traffic_gb=50,
            price=Decimal("99.00"),
            currency=Currency.RUB,
        )
        s.add(plan)
        await s.commit()
        await s.refresh(plan)
        plan_id = plan.id

    pay_dto = PaymentCreate(
        telegram_id=user.telegram_id,
        plan_id=plan_id,
        provider=PaymentProvider.TEST,
    )
    pay_resp = await client.post(
        f"{API_PREFIX}/payments", json=pay_dto.model_dump(mode="json"), headers=bot_headers
    )
    assert pay_resp.status_code == 200, pay_resp.text
    payment = PaymentOut.model_validate(pay_resp.json())

    # Simulate webhook success by calling the test provider webhook.
    webhook_resp = await client.post(
        f"{API_PREFIX}/payments/webhook/test",
        json={"provider_payment_id": payment.provider_payment_id, "status": "succeeded"},
    )
    assert webhook_resp.status_code == 200, webhook_resp.text

    # Fetch issued VPN for the subscription.
    refreshed = await client.get(f"{API_PREFIX}/payments/{payment.id}", headers=bot_headers)
    assert refreshed.status_code == 200
    sub_id = refreshed.json()["subscription_id"]
    issued = await client.get(f"{API_PREFIX}/subscriptions/{sub_id}/issued", headers=bot_headers)
    assert issued.status_code == 200, issued.text
    body = issued.json()
    assert body["vless_link"].startswith("vless://")
    assert body["happ_import_url"].startswith("happ://")
    assert body["qr_png_base64"]


pytestmark = pytest.mark.asyncio
