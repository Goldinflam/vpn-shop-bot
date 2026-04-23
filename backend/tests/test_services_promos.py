"""Tests for PromoService and trial logic."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest
from backend.models import PromoCode, User
from backend.services.promos import PromoService
from backend.services.subscriptions import SubscriptionService
from shared.contracts.errors import (
    PromoAlreadyUsedError,
    PromoExhaustedError,
    PromoExpiredError,
    PromoNotFoundError,
    TrialAlreadyClaimedError,
)
from shared.contracts.xui import XUIClientProtocol
from sqlalchemy.ext.asyncio import AsyncSession


@pytest.fixture
def subscription_service(
    session: AsyncSession, xui_mock: XUIClientProtocol
) -> SubscriptionService:
    return SubscriptionService(session, xui_mock)


@pytest.fixture
def promo_service(
    session: AsyncSession, subscription_service: SubscriptionService
) -> PromoService:
    return PromoService(session, subscription_service)


async def _add_user(session: AsyncSession, telegram_id: int = 4242) -> User:
    user = User(telegram_id=telegram_id, username="tester")
    session.add(user)
    await session.commit()
    await session.refresh(user)
    return user


async def _add_promo(session: AsyncSession, **kwargs: object) -> PromoCode:
    defaults: dict[str, object] = {
        "code": "FREE1",
        "is_trial": True,
        "trial_days": 1,
        "trial_traffic_gb": 2,
        "per_user_limit": 1,
    }
    defaults.update(kwargs)
    promo = PromoCode(**defaults)  # type: ignore[arg-type]
    session.add(promo)
    await session.commit()
    await session.refresh(promo)
    return promo


async def test_create_trial_issues_vpn(
    session: AsyncSession, promo_service: PromoService
) -> None:
    user = await _add_user(session)
    result = await promo_service.create_trial(user.telegram_id)
    assert result.vless_link.startswith("vless://")
    assert result.happ_import_url.startswith("happ://")
    assert result.qr_png_base64
    await session.refresh(user)
    assert user.trial_used is True


async def test_create_trial_twice_rejected(
    session: AsyncSession, promo_service: PromoService
) -> None:
    user = await _add_user(session)
    await promo_service.create_trial(user.telegram_id)
    with pytest.raises(TrialAlreadyClaimedError):
        await promo_service.create_trial(user.telegram_id)


async def test_apply_trial_promo_issues_vpn(
    session: AsyncSession, promo_service: PromoService
) -> None:
    user = await _add_user(session)
    await _add_promo(session, code="FREE7", trial_days=7, trial_traffic_gb=10)
    result = await promo_service.apply_promo(user.telegram_id, "free7")
    assert result.is_trial is True
    assert result.issued is not None
    assert result.issued.vless_link.startswith("vless://")
    assert result.discount_percent is None
    await session.refresh(user)
    assert user.trial_used is True


async def test_apply_promo_unknown_code(
    session: AsyncSession, promo_service: PromoService
) -> None:
    await _add_user(session)
    with pytest.raises(PromoNotFoundError):
        await promo_service.apply_promo(4242, "DOESNOTEXIST")


async def test_apply_promo_inactive_rejected(
    session: AsyncSession, promo_service: PromoService
) -> None:
    user = await _add_user(session)
    await _add_promo(session, code="OLD", is_active=False)
    with pytest.raises(PromoNotFoundError):
        await promo_service.apply_promo(user.telegram_id, "OLD")


async def test_apply_promo_expired(
    session: AsyncSession, promo_service: PromoService
) -> None:
    user = await _add_user(session)
    past = datetime.now(UTC) - timedelta(days=1)
    await _add_promo(session, code="PAST", valid_until=past)
    with pytest.raises(PromoExpiredError):
        await promo_service.apply_promo(user.telegram_id, "PAST")


async def test_apply_promo_not_yet_active(
    session: AsyncSession, promo_service: PromoService
) -> None:
    user = await _add_user(session)
    future = datetime.now(UTC) + timedelta(days=1)
    await _add_promo(session, code="FUTURE", valid_from=future)
    with pytest.raises(PromoExpiredError):
        await promo_service.apply_promo(user.telegram_id, "FUTURE")


async def test_apply_promo_global_limit_exhausted(
    session: AsyncSession, promo_service: PromoService
) -> None:
    user = await _add_user(session)
    await _add_promo(session, code="ONLY1", usage_limit=1, used_count=1)
    with pytest.raises(PromoExhaustedError):
        await promo_service.apply_promo(user.telegram_id, "ONLY1")


async def test_apply_promo_per_user_limit(
    session: AsyncSession, promo_service: PromoService
) -> None:
    user = await _add_user(session)
    await _add_promo(session, code="FREE1")
    # first redemption consumes trial
    await promo_service.apply_promo(user.telegram_id, "FREE1")
    with pytest.raises((PromoAlreadyUsedError, TrialAlreadyClaimedError)):
        await promo_service.apply_promo(user.telegram_id, "FREE1")


async def test_apply_discount_promo(
    session: AsyncSession, promo_service: PromoService
) -> None:
    user = await _add_user(session)
    await _add_promo(
        session,
        code="SAVE20",
        is_trial=False,
        trial_days=None,
        trial_traffic_gb=None,
        discount_percent=20,
    )
    result = await promo_service.apply_promo(user.telegram_id, "SAVE20")
    assert result.is_trial is False
    assert result.discount_percent == 20
    assert result.issued is None
    await session.refresh(user)
    assert user.trial_used is False
