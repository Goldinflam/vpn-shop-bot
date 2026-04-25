"""Subscription service.

Multi-server: every provisioning call (paid, trial, promo) iterates all
``enabled=True`` servers via :class:`XUIPool`, creates a VLESS client on
each, and persists one ``subscription_clients`` row per success. The
subscription is considered ACTIVE if at least one server succeeds.
"""

from __future__ import annotations

import contextlib
import logging
import secrets
from datetime import UTC, datetime, timedelta

from shared.contracts.errors import (
    NotFoundError,
    SubscriptionError,
    XUIError,
)
from shared.contracts.xui import VlessClientResult, XUIClientProtocol
from shared.enums import SubscriptionStatus
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.config import Settings, get_settings
from backend.models import (
    Payment,
    Plan,
    Server,
    Subscription,
    SubscriptionClient,
    User,
)
from backend.xui_pool import XUIPool, list_enabled_servers

logger = logging.getLogger(__name__)

_BYTES_PER_GB = 1024 * 1024 * 1024


TRIAL_PLAN_NAME = "__trial__"


def _as_utc(value: datetime) -> datetime:
    """Return a UTC-aware copy of ``value``.

    SQLite's aiosqlite driver drops tzinfo on read even when the column is
    declared ``DateTime(timezone=True)``. Normalize to UTC before comparing
    against ``datetime.now(timezone.utc)``.
    """
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)


def _new_sub_token() -> str:
    return secrets.token_hex(16)


class SubscriptionService:
    """Business logic for ``Subscription`` entities."""

    def __init__(
        self,
        session: AsyncSession,
        xui_pool: XUIPool,
        settings: Settings | None = None,
    ) -> None:
        self._session = session
        self._pool = xui_pool
        self._settings = settings or get_settings()

    # ----------------------------- helpers -----------------------------

    async def _client_for(self, server: Server) -> XUIClientProtocol:
        return await self._pool.get(server)

    async def _provision_on_servers(
        self,
        *,
        servers: list[Server],
        email_base: str,
        expire_ts_ms: int,
        traffic_limit_bytes: int,
        telegram_id: int | None,
    ) -> list[tuple[Server, VlessClientResult]]:
        """Try to create a VLESS client on each *server*. Returns successes."""
        successes: list[tuple[Server, VlessClientResult]] = []
        for server in servers:
            try:
                client = await self._client_for(server)
                result = await client.create_vless_client(
                    inbound_id=server.inbound_id,
                    email=f"{email_base}-srv{server.id}",
                    expire_ts_ms=expire_ts_ms,
                    traffic_limit_bytes=traffic_limit_bytes,
                    telegram_id=telegram_id,
                )
            except XUIError as exc:
                logger.exception(
                    "x-ui create failed on server %s (%s): %s", server.name, server.host, exc
                )
                continue
            successes.append((server, result))
        return successes

    @staticmethod
    def _persist_clients(
        subscription: Subscription,
        successes: list[tuple[Server, VlessClientResult]],
    ) -> None:
        for server, result in successes:
            subscription.clients.append(
                SubscriptionClient(
                    server_id=server.id,
                    xui_inbound_id=result.inbound_id,
                    xui_client_uuid=result.client_uuid,
                    xui_email=result.email,
                    vless_link=result.vless_link,
                    enabled=True,
                )
            )

    def _public_subscription_url(self, sub_token: str) -> str | None:
        base = self._settings.public_sub_base_url.rstrip("/")
        if not base:
            return None
        return f"{base}/sub/{sub_token}"

    # ----------------------------- API -----------------------------

    async def create_from_payment(self, payment: Payment) -> Subscription:
        """Provision a multi-server subscription and persist it."""
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
        # 0 GB plan = unlimited; XUI accepts 0 as no-limit.
        traffic_limit = plan.traffic_gb * _BYTES_PER_GB
        return await self._provision(
            user=user,
            plan=plan,
            now=now,
            expires_at=expires_at,
            traffic_limit_bytes=traffic_limit,
            email_base=f"tg{user.telegram_id}-{int(now.timestamp())}",
            payment=payment,
        )

    async def create_free(
        self,
        *,
        user: User,
        days: int | None = None,
        hours: int | None = None,
        traffic_gb: int | None = None,
    ) -> Subscription:
        """Provision a multi-server trial subscription.

        Defaults come from ``Settings.trial_duration_hours`` /
        ``trial_traffic_gb`` (24 h / 10 GB) when neither *days*/*hours* nor
        *traffic_gb* is given.
        """
        cfg = self._settings
        if hours is None and days is None:
            hours = cfg.trial_duration_hours
        traffic_gb = traffic_gb if traffic_gb is not None else cfg.trial_traffic_gb
        plan = await self._get_or_create_trial_plan(
            duration_days=(days if days is not None else max(1, (hours or 24) // 24)),
            traffic_gb=traffic_gb,
        )
        now = datetime.now(UTC)
        delta = (
            timedelta(days=days)
            if days is not None
            else timedelta(hours=hours or cfg.trial_duration_hours)
        )
        expires_at = now + delta
        traffic_limit = traffic_gb * _BYTES_PER_GB
        return await self._provision(
            user=user,
            plan=plan,
            now=now,
            expires_at=expires_at,
            traffic_limit_bytes=traffic_limit,
            email_base=f"tg{user.telegram_id}-trial-{int(now.timestamp())}",
            payment=None,
        )

    async def _provision(
        self,
        *,
        user: User,
        plan: Plan,
        now: datetime,
        expires_at: datetime,
        traffic_limit_bytes: int,
        email_base: str,
        payment: Payment | None,
    ) -> Subscription:
        servers = await list_enabled_servers(self._session)
        if not servers:
            raise SubscriptionError(
                "No enabled servers configured. Add at least one via POST /api/v1/admin/servers."
            )

        successes = await self._provision_on_servers(
            servers=servers,
            email_base=email_base,
            expire_ts_ms=int(expires_at.timestamp() * 1000),
            traffic_limit_bytes=traffic_limit_bytes,
            telegram_id=user.telegram_id,
        )
        if not successes:
            raise SubscriptionError(
                "Failed to create VLESS client on any of the configured servers"
            )

        primary_server, primary_result = successes[0]
        sub_token = _new_sub_token()
        subscription = Subscription(
            user_id=user.id,
            plan_id=plan.id,
            sub_token=sub_token,
            xui_client_uuid=primary_result.client_uuid,
            xui_inbound_id=primary_result.inbound_id,
            xui_email=primary_result.email,
            vless_link=primary_result.vless_link,
            subscription_url=self._public_subscription_url(sub_token),
            traffic_limit_bytes=traffic_limit_bytes,
            traffic_used_bytes=0,
            starts_at=now,
            expires_at=expires_at,
            status=SubscriptionStatus.ACTIVE,
        )
        self._persist_clients(subscription, successes)
        self._session.add(subscription)
        await self._session.flush()

        if payment is not None:
            payment.subscription_id = subscription.id
        await self._session.flush()
        await self._session.refresh(subscription, attribute_names=["clients"])
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

        # Refresh clients in DB so sub.clients is populated.
        await self._session.refresh(subscription, attribute_names=["clients"])
        any_extended = False
        for sub_client in subscription.clients:
            server = await self._session.get(Server, sub_client.server_id)
            if server is None or not server.enabled:
                continue
            try:
                client = await self._client_for(server)
                await client.extend_client(
                    inbound_id=sub_client.xui_inbound_id,
                    client_uuid=sub_client.xui_client_uuid,
                    expire_ts_ms=int(new_expiry.timestamp() * 1000),
                    traffic_limit_bytes=new_limit,
                )
            except XUIError:
                logger.exception(
                    "x-ui extend failed on server %s for sub %s",
                    sub_client.server_id,
                    subscription.id,
                )
                continue
            any_extended = True

        if not any_extended:
            raise SubscriptionError("Failed to extend the subscription on any active server")

        subscription.expires_at = new_expiry
        subscription.traffic_limit_bytes = new_limit
        subscription.status = SubscriptionStatus.ACTIVE
        await self._session.flush()
        await self._session.refresh(subscription)
        return subscription

    async def _get_or_create_trial_plan(self, *, duration_days: int, traffic_gb: int) -> Plan:
        from decimal import Decimal

        from shared.enums import Currency

        result = await self._session.execute(select(Plan).where(Plan.name == TRIAL_PLAN_NAME))
        plan = result.scalar_one_or_none()
        if plan is None:
            plan = Plan(
                name=TRIAL_PLAN_NAME,
                description="Reserved plan for trial / promo subscriptions",
                duration_days=max(1, duration_days),
                traffic_gb=traffic_gb,
                price=Decimal("0"),
                currency=Currency.RUB,
                is_active=False,
                sort_order=-1,
            )
            self._session.add(plan)
            await self._session.flush()
            await self._session.refresh(plan)
        return plan

    async def get(self, subscription_id: int) -> Subscription:
        sub = await self._session.get(Subscription, subscription_id)
        if sub is None:
            raise NotFoundError(f"Subscription with id={subscription_id} not found")
        return sub

    async def get_by_token(self, sub_token: str) -> Subscription:
        result = await self._session.execute(
            select(Subscription).where(Subscription.sub_token == sub_token)
        )
        sub = result.scalar_one_or_none()
        if sub is None:
            raise NotFoundError(f"Subscription token {sub_token!r} not found")
        return sub

    async def list_for_user(self, user_id: int) -> list[Subscription]:
        result = await self._session.execute(
            select(Subscription)
            .where(Subscription.user_id == user_id)
            .order_by(Subscription.created_at.desc())
        )
        return list(result.scalars().all())

    async def list_active_clients_for_token(self, sub_token: str) -> list[SubscriptionClient]:
        """Return ``subscription_clients`` rows for an active token,
        filtered to currently ``enabled=True`` servers."""
        sub = await self.get_by_token(sub_token)
        if sub.status != SubscriptionStatus.ACTIVE:
            return []
        await self._session.refresh(sub, attribute_names=["clients"])
        out: list[SubscriptionClient] = []
        for sub_client in sub.clients:
            server = await self._session.get(Server, sub_client.server_id)
            if server is None or not server.enabled or not sub_client.enabled:
                continue
            out.append(sub_client)
        return out

    async def expire_overdue(self) -> int:
        """Mark expired subscriptions and disable their clients on every server."""
        now = datetime.now(UTC)
        result = await self._session.execute(
            select(Subscription).where(
                Subscription.expires_at < now,
                Subscription.status == SubscriptionStatus.ACTIVE,
            )
        )
        overdue = list(result.scalars().all())
        for sub in overdue:
            await self._session.refresh(sub, attribute_names=["clients"])
            for sub_client in sub.clients:
                server = await self._session.get(Server, sub_client.server_id)
                if server is None:
                    continue
                with contextlib.suppress(XUIError):
                    client = await self._client_for(server)
                    await client.disable_client(
                        inbound_id=sub_client.xui_inbound_id,
                        client_uuid=sub_client.xui_client_uuid,
                    )
                sub_client.enabled = False
            sub.status = SubscriptionStatus.EXPIRED
        await self._session.flush()
        return len(overdue)
