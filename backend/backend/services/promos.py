"""Promo-code and trial subscription service."""

from __future__ import annotations

from datetime import UTC, datetime

from shared.contracts.errors import (
    NotFoundError,
    PromoAlreadyUsedError,
    PromoError,
    PromoExhaustedError,
    PromoExpiredError,
    PromoNotFoundError,
    TrialAlreadyClaimedError,
)
from shared.schemas import IssuedVpnOut, PromoApplyOut
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.models import PromoCode, PromoUsage, User
from backend.services.issuance import issued_vpn_from_subscription
from backend.services.subscriptions import SubscriptionService


def _as_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)


class PromoService:
    """Validate and redeem promo codes; issue trial subscriptions."""

    def __init__(
        self,
        session: AsyncSession,
        subscription_service: SubscriptionService,
    ) -> None:
        self._session = session
        self._subscriptions = subscription_service

    async def _get_user(self, telegram_id: int) -> User:
        result = await self._session.execute(select(User).where(User.telegram_id == telegram_id))
        user = result.scalar_one_or_none()
        if user is None:
            raise NotFoundError(f"User with telegram_id={telegram_id} not found")
        return user

    async def create_trial(self, telegram_id: int) -> IssuedVpnOut:
        """Issue the default free trial (24 h / 10 GB by default) to a user
        who hasn't claimed one. Duration and traffic come from
        ``Settings.trial_duration_hours`` / ``trial_traffic_gb``.
        """
        user = await self._get_user(telegram_id)
        if user.trial_used:
            raise TrialAlreadyClaimedError(
                f"User telegram_id={telegram_id} has already claimed their trial"
            )
        # ``create_free`` picks up trial defaults from settings when the
        # caller passes neither ``days``/``hours`` nor ``traffic_gb``.
        subscription = await self._subscriptions.create_free(user=user)
        user.trial_used = True
        await self._session.flush()
        await self._session.refresh(subscription)
        return issued_vpn_from_subscription(subscription)

    async def apply_promo(self, telegram_id: int, code: str) -> PromoApplyOut:
        """Redeem a promo code.

        Trial promos immediately provision a subscription and return
        ``IssuedVpnOut`` inside the response. Discount promos return a
        ``discount_percent`` the bot uses on the next paid purchase.
        """
        user = await self._get_user(telegram_id)
        promo = await self._load_active_promo(code)
        self._check_window(promo)
        self._check_global_limit(promo)
        await self._check_per_user_limit(promo, user)

        if promo.is_trial:
            return await self._redeem_trial_promo(promo, user)
        return await self._redeem_discount_promo(promo, user)

    async def _load_active_promo(self, code: str) -> PromoCode:
        normalized = code.strip().upper()
        result = await self._session.execute(select(PromoCode).where(PromoCode.code == normalized))
        promo = result.scalar_one_or_none()
        if promo is None or not promo.is_active:
            raise PromoNotFoundError(f"Promo code '{normalized}' not found")
        return promo

    @staticmethod
    def _check_window(promo: PromoCode) -> None:
        now = datetime.now(UTC)
        if promo.valid_from is not None and _as_utc(promo.valid_from) > now:
            raise PromoExpiredError(f"Promo '{promo.code}' is not yet active")
        if promo.valid_until is not None and _as_utc(promo.valid_until) < now:
            raise PromoExpiredError(f"Promo '{promo.code}' has expired")

    @staticmethod
    def _check_global_limit(promo: PromoCode) -> None:
        if promo.usage_limit is not None and promo.used_count >= promo.usage_limit:
            raise PromoExhaustedError(f"Promo '{promo.code}' is exhausted")

    async def _check_per_user_limit(self, promo: PromoCode, user: User) -> None:
        result = await self._session.execute(
            select(PromoUsage).where(
                PromoUsage.promo_code_id == promo.id,
                PromoUsage.user_id == user.id,
            )
        )
        count = len(list(result.scalars().all()))
        if count >= promo.per_user_limit:
            raise PromoAlreadyUsedError(f"User already redeemed promo '{promo.code}'")

    async def _redeem_trial_promo(self, promo: PromoCode, user: User) -> PromoApplyOut:
        if promo.trial_days is None or promo.trial_traffic_gb is None:
            raise PromoError(
                f"Promo '{promo.code}' is marked trial but missing trial_days/trial_traffic_gb"
            )
        if user.trial_used:
            raise TrialAlreadyClaimedError(
                f"User telegram_id={user.telegram_id} has already claimed a trial"
            )

        subscription = await self._subscriptions.create_free(
            user=user,
            days=promo.trial_days,
            traffic_gb=promo.trial_traffic_gb or 0,
        )
        user.trial_used = True

        usage = PromoUsage(
            promo_code_id=promo.id,
            user_id=user.id,
            subscription_id=subscription.id,
        )
        self._session.add(usage)
        promo.used_count += 1
        await self._session.flush()
        await self._session.refresh(subscription)

        return PromoApplyOut(
            code=promo.code,
            is_trial=True,
            issued=issued_vpn_from_subscription(subscription),
        )

    async def _redeem_discount_promo(self, promo: PromoCode, user: User) -> PromoApplyOut:
        if promo.discount_percent is None or not (0 < promo.discount_percent <= 100):
            raise PromoError(
                f"Promo '{promo.code}' has invalid discount_percent={promo.discount_percent}"
            )
        usage = PromoUsage(promo_code_id=promo.id, user_id=user.id)
        self._session.add(usage)
        promo.used_count += 1
        await self._session.flush()
        return PromoApplyOut(
            code=promo.code,
            is_trial=False,
            discount_percent=promo.discount_percent,
        )
