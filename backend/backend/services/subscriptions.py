"""Subscription service."""

from __future__ import annotations

import contextlib
from datetime import UTC, datetime, timedelta

from shared.contracts.errors import (
    NotFoundError,
    SubscriptionError,
    XUIError,
)
from shared.contracts.xui import XUIClientProtocol
from shared.enums import SubscriptionStatus
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.config import Settings, get_settings
from backend.models import Payment, Plan, Subscription, User

_BYTES_PER_GB = 1024 * 1024 * 1024


def _as_utc(value: datetime) -> datetime:
    """Return a UTC-aware copy of ``value``.

    SQLite's aiosqlite driver drops tzinfo on read even when the column is
    declared ``DateTime(timezone=True)``. Normalize to UTC before comparing
    against ``datetime.now(timezone.utc)``.
    """
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)


class SubscriptionService:
    """Business logic for ``Subscription`` entities."""

    def __init__(
        self,
        session: AsyncSession,
        xui_client: XUIClientProtocol,
        settings: Settings | None = None,
    ) -> None:
        self._session = session
        self._xui = xui_client
        self._settings = settings or get_settings()

    async def create_from_payment(self, payment: Payment) -> Subscription:
        """Provision a VLESS client on the x-ui panel and persist the subscription."""
        if payment.subscription_id is not None:
            subscription = await self._session.get(Subscription, payment.subscription_id)
            if subscription is None:
                raise NotFoundError(
                    f"Subscription {payment.subscription_id} referenced by payment not found"
                )
            return await self._extend_subscription(subscription, payment)

        return await self._create_new_subscription(payment)

    async def _create_new_subscription(self, payment: Payment) -> Subscription:
        user = await self._session.get(User, payment.user_id)
        if user is None:
            raise NotFoundError(f"User {payment.user_id} not found")
        plan = await self._session.get(Plan, payment.plan_id)
        if plan is None:
            raise NotFoundError(f"Plan {payment.plan_id} not found")

        now = datetime.now(UTC)
        expires_at = now + timedelta(days=plan.duration_days)
        traffic_limit = plan.traffic_gb * _BYTES_PER_GB
        email = f"tg{user.telegram_id}-{int(now.timestamp())}"
        inbound_id = self._settings.xui_inbound_id

        try:
            result = await self._xui.create_vless_client(
                inbound_id=inbound_id,
                email=email,
                expire_ts_ms=int(expires_at.timestamp() * 1000),
                traffic_limit_bytes=traffic_limit,
                telegram_id=user.telegram_id,
            )
        except XUIError as exc:
            raise SubscriptionError(f"Failed to create VLESS client: {exc}") from exc

        subscription = Subscription(
            user_id=user.id,
            plan_id=plan.id,
            xui_client_uuid=result.client_uuid,
            xui_inbound_id=result.inbound_id,
            xui_email=result.email,
            vless_link=result.vless_link,
            traffic_limit_bytes=traffic_limit,
            traffic_used_bytes=0,
            starts_at=now,
            expires_at=expires_at,
            status=SubscriptionStatus.ACTIVE,
        )
        self._session.add(subscription)
        await self._session.flush()

        payment.subscription_id = subscription.id
        await self._session.flush()
        await self._session.refresh(subscription)
        return subscription

    async def _extend_subscription(
        self, subscription: Subscription, payment: Payment
    ) -> Subscription:
        plan = await self._session.get(Plan, payment.plan_id)
        if plan is None:
            raise NotFoundError(f"Plan {payment.plan_id} not found")

        now = datetime.now(UTC)
        current_expiry = _as_utc(subscription.expires_at)
        base = current_expiry if current_expiry > now else now
        new_expiry = base + timedelta(days=plan.duration_days)
        new_limit = subscription.traffic_limit_bytes + plan.traffic_gb * _BYTES_PER_GB

        try:
            await self._xui.extend_client(
                inbound_id=subscription.xui_inbound_id,
                client_uuid=subscription.xui_client_uuid,
                expire_ts_ms=int(new_expiry.timestamp() * 1000),
                traffic_limit_bytes=new_limit,
            )
        except XUIError as exc:
            raise SubscriptionError(f"Failed to extend VLESS client: {exc}") from exc

        subscription.expires_at = new_expiry
        subscription.traffic_limit_bytes = new_limit
        subscription.status = SubscriptionStatus.ACTIVE
        await self._session.flush()
        await self._session.refresh(subscription)
        return subscription

    async def get(self, subscription_id: int) -> Subscription:
        sub = await self._session.get(Subscription, subscription_id)
        if sub is None:
            raise NotFoundError(f"Subscription with id={subscription_id} not found")
        return sub

    async def list_for_user(self, user_id: int) -> list[Subscription]:
        result = await self._session.execute(
            select(Subscription)
            .where(Subscription.user_id == user_id)
            .order_by(Subscription.created_at.desc())
        )
        return list(result.scalars().all())

    async def expire_overdue(self) -> int:
        """Mark expired subscriptions and disable them in the x-ui panel."""
        now = datetime.now(UTC)
        result = await self._session.execute(
            select(Subscription).where(
                Subscription.expires_at < now,
                Subscription.status == SubscriptionStatus.ACTIVE,
            )
        )
        overdue = list(result.scalars().all())
        for sub in overdue:
            with contextlib.suppress(XUIError):
                await self._xui.disable_client(
                    inbound_id=sub.xui_inbound_id,
                    client_uuid=sub.xui_client_uuid,
                )
            sub.status = SubscriptionStatus.EXPIRED
        await self._session.flush()
        return len(overdue)
