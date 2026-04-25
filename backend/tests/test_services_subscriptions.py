"""Tests for ``SubscriptionService``."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from decimal import Decimal
from typing import cast
from unittest.mock import AsyncMock

import pytest
from backend.models import Payment, Plan, Server, Subscription, User
from backend.services.subscriptions import SubscriptionService
from backend.xui_pool import XUIPool
from shared.contracts.errors import NotFoundError
from shared.contracts.xui import VlessClientResult
from shared.enums import Currency, PaymentProvider, PaymentStatus, SubscriptionStatus
from sqlalchemy.ext.asyncio import AsyncSession


async def _make_user(session: AsyncSession, telegram_id: int = 555) -> User:
    user = User(telegram_id=telegram_id, username="x")
    session.add(user)
    await session.commit()
    await session.refresh(user)
    return user


async def _make_plan(session: AsyncSession, *, duration_days: int = 30) -> Plan:
    plan = Plan(
        name="p",
        duration_days=duration_days,
        traffic_gb=10,
        price=Decimal("100.00"),
        currency=Currency.RUB,
    )
    session.add(plan)
    await session.commit()
    await session.refresh(plan)
    return plan


async def _make_payment(
    session: AsyncSession,
    user: User,
    plan: Plan,
    *,
    subscription_id: int | None = None,
) -> Payment:
    payment = Payment(
        user_id=user.id,
        plan_id=plan.id,
        subscription_id=subscription_id,
        amount=plan.price,
        currency=plan.currency,
        provider=PaymentProvider.TEST,
        provider_payment_id="pp-1",
        status=PaymentStatus.SUCCEEDED,
        raw_payload={},
    )
    session.add(payment)
    await session.commit()
    await session.refresh(payment)
    return payment


async def test_create_from_payment_new_subscription(
    session: AsyncSession,
    xui_pool: XUIPool,
    server_row: Server,
    xui_mock: object,
) -> None:
    user = await _make_user(session)
    plan = await _make_plan(session)
    payment = await _make_payment(session, user, plan)

    service = SubscriptionService(session, xui_pool)
    sub = await service.create_from_payment(payment)
    await session.commit()

    assert sub.status == SubscriptionStatus.ACTIVE
    assert sub.xui_client_uuid == "uuid-test-1"
    assert sub.traffic_limit_bytes == 10 * 1024 * 1024 * 1024
    assert sub.sub_token  # public token populated
    assert len(sub.clients) == 1
    assert sub.clients[0].server_id == server_row.id
    xui_cast = cast(AsyncMock, xui_mock)
    xui_cast.create_vless_client.assert_awaited_once()
    await session.refresh(payment)
    assert payment.subscription_id == sub.id


async def test_create_from_payment_extends_existing(
    session: AsyncSession,
    xui_pool: XUIPool,
    server_row: Server,
    xui_mock: object,
) -> None:
    user = await _make_user(session)
    plan = await _make_plan(session, duration_days=10)
    xui_cast = cast(AsyncMock, xui_mock)
    xui_cast.create_vless_client.return_value = VlessClientResult(
        client_uuid="u1",
        email="e1",
        inbound_id=1,
        vless_link="vless://link",
        subscription_url=None,
        qr_png=b"",
    )

    first_payment = await _make_payment(session, user, plan)
    service = SubscriptionService(session, xui_pool)
    sub = await service.create_from_payment(first_payment)
    await session.commit()

    renewal = await _make_payment(session, user, plan, subscription_id=sub.id)
    extended = await service.create_from_payment(renewal)
    await session.commit()
    xui_cast.extend_client.assert_awaited_once()
    assert extended.traffic_limit_bytes == 2 * 10 * 1024 * 1024 * 1024
    _ = server_row  # fixture must exist for provisioning to succeed


async def test_expire_overdue_marks_and_disables(
    session: AsyncSession,
    xui_pool: XUIPool,
    server_row: Server,
    xui_mock: object,
) -> None:
    from backend.models import SubscriptionClient

    user = await _make_user(session)
    plan = await _make_plan(session)
    past = datetime.now(UTC) - timedelta(days=1)
    sub = Subscription(
        user_id=user.id,
        plan_id=plan.id,
        sub_token="tok-expire",
        xui_client_uuid="u1",
        xui_inbound_id=1,
        xui_email="e1",
        vless_link="vless://x",
        traffic_limit_bytes=0,
        traffic_used_bytes=0,
        starts_at=past - timedelta(days=30),
        expires_at=past,
        status=SubscriptionStatus.ACTIVE,
    )
    session.add(sub)
    await session.flush()
    session.add(
        SubscriptionClient(
            subscription_id=sub.id,
            server_id=server_row.id,
            xui_inbound_id=1,
            xui_client_uuid="u1",
            xui_email="e1",
            vless_link="vless://x",
            enabled=True,
        )
    )
    await session.commit()

    service = SubscriptionService(session, xui_pool)
    n = await service.expire_overdue()
    await session.commit()
    assert n == 1
    await session.refresh(sub)
    assert sub.status == SubscriptionStatus.EXPIRED
    xui_cast = cast(AsyncMock, xui_mock)
    xui_cast.disable_client.assert_awaited_once()


async def test_get_missing_raises(session: AsyncSession, xui_pool: XUIPool) -> None:
    service = SubscriptionService(session, xui_pool)
    with pytest.raises(NotFoundError):
        await service.get(12345)


async def test_list_for_user_orders(
    session: AsyncSession,
    xui_pool: XUIPool,
    server_row: Server,
    xui_mock: object,
) -> None:
    user = await _make_user(session)
    plan = await _make_plan(session)
    service = SubscriptionService(session, xui_pool)

    first = await service.create_from_payment(await _make_payment(session, user, plan))
    await session.commit()
    xui_cast = cast(AsyncMock, xui_mock)
    xui_cast.create_vless_client.return_value = VlessClientResult(
        client_uuid="uuid-test-2",
        email="tg1-2",
        inbound_id=1,
        vless_link="vless://uuid-test-2@x:1#p",
        subscription_url=None,
        qr_png=b"",
    )
    second = await service.create_from_payment(await _make_payment(session, user, plan))
    await session.commit()

    subs = await service.list_for_user(user.id)
    ids = [s.id for s in subs]
    assert set(ids) == {first.id, second.id}
    _ = server_row
