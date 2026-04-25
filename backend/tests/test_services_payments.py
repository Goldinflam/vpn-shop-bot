"""Tests for ``PaymentService`` and payment adapters."""

from __future__ import annotations

import json
from decimal import Decimal
from typing import cast
from unittest.mock import AsyncMock

import pytest
from backend.models import Plan, Server, User
from backend.payments import TestAdapter
from backend.services.payments import PaymentService
from backend.services.subscriptions import SubscriptionService
from backend.xui_pool import XUIPool
from shared.contracts.errors import NotFoundError
from shared.contracts.xui import XUIClientProtocol
from shared.enums import Currency, PaymentProvider, PaymentStatus
from shared.schemas import PaymentCreate
from sqlalchemy.ext.asyncio import AsyncSession


async def _seed(session: AsyncSession) -> tuple[User, Plan]:
    user = User(telegram_id=2001, username="pay")
    plan = Plan(
        name="30d",
        duration_days=30,
        traffic_gb=20,
        price=Decimal("150.00"),
        currency=Currency.RUB,
    )
    session.add_all([user, plan])
    await session.commit()
    await session.refresh(user)
    await session.refresh(plan)
    return user, plan


async def test_create_payment_uses_test_adapter(
    session: AsyncSession, xui_pool: XUIPool, server_row: Server
) -> None:
    user, plan = await _seed(session)
    _ = server_row
    subs = SubscriptionService(session, xui_pool)
    service = PaymentService(session, subs, adapters={PaymentProvider.TEST: TestAdapter()})

    payment = await service.create(
        PaymentCreate(telegram_id=user.telegram_id, plan_id=plan.id, provider=PaymentProvider.TEST)
    )
    await session.commit()
    assert payment.status == PaymentStatus.PENDING
    assert payment.provider_payment_id is not None
    assert payment.amount == plan.price


async def test_create_payment_user_not_found(session: AsyncSession, xui_pool: XUIPool) -> None:
    subs = SubscriptionService(session, xui_pool)
    service = PaymentService(session, subs, adapters={PaymentProvider.TEST: TestAdapter()})
    with pytest.raises(NotFoundError):
        await service.create(
            PaymentCreate(telegram_id=999, plan_id=1, provider=PaymentProvider.TEST)
        )


async def test_webhook_succeeds_creates_subscription(
    session: AsyncSession,
    xui_pool: XUIPool,
    xui_mock: XUIClientProtocol,
    server_row: Server,
) -> None:
    user, plan = await _seed(session)
    _ = server_row
    subs = SubscriptionService(session, xui_pool)
    service = PaymentService(session, subs, adapters={PaymentProvider.TEST: TestAdapter()})

    payment = await service.create(
        PaymentCreate(telegram_id=user.telegram_id, plan_id=plan.id, provider=PaymentProvider.TEST)
    )
    await session.commit()

    body = json.dumps(
        {"provider_payment_id": payment.provider_payment_id, "status": "succeeded"}
    ).encode()
    result = await service.handle_webhook(PaymentProvider.TEST, body, {})
    await session.commit()

    assert result is not None
    assert result.status == PaymentStatus.SUCCEEDED
    assert result.subscription_id is not None
    xui_cast = cast(AsyncMock, xui_mock)
    xui_cast.create_vless_client.assert_awaited_once()


async def test_webhook_unknown_payment_returns_none(
    session: AsyncSession, xui_pool: XUIPool
) -> None:
    subs = SubscriptionService(session, xui_pool)
    service = PaymentService(session, subs, adapters={PaymentProvider.TEST: TestAdapter()})
    body = json.dumps({"provider_payment_id": "never-seen", "status": "succeeded"}).encode()
    result = await service.handle_webhook(PaymentProvider.TEST, body, {})
    assert result is None
