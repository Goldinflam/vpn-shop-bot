"""Payment service — orchestrates providers, persistence, and subscription provisioning."""

from __future__ import annotations

from collections.abc import Mapping

from shared.contracts.errors import NotFoundError, PaymentError
from shared.enums import PaymentProvider, PaymentStatus
from shared.schemas import PaymentCreate
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.models import Payment, Plan, Subscription, User
from backend.payments import (
    PaymentProviderAdapter,
    WebhookVerificationResult,
    build_adapter_registry,
)
from backend.services.subscriptions import SubscriptionService


class PaymentService:
    """Business logic for ``Payment`` entities and webhook orchestration."""

    def __init__(
        self,
        session: AsyncSession,
        subscription_service: SubscriptionService,
        adapters: dict[PaymentProvider, PaymentProviderAdapter] | None = None,
    ) -> None:
        self._session = session
        self._subscriptions = subscription_service
        self._adapters = adapters if adapters is not None else build_adapter_registry()

    def _get_adapter(self, provider: PaymentProvider) -> PaymentProviderAdapter:
        adapter = self._adapters.get(provider)
        if adapter is None:
            raise PaymentError(f"No adapter configured for provider={provider.value}")
        return adapter

    async def create(self, dto: PaymentCreate) -> Payment:
        user_result = await self._session.execute(
            select(User).where(User.telegram_id == dto.telegram_id)
        )
        user = user_result.scalar_one_or_none()
        if user is None:
            raise NotFoundError(f"User with telegram_id={dto.telegram_id} not found")

        plan = await self._session.get(Plan, dto.plan_id)
        if plan is None:
            raise NotFoundError(f"Plan with id={dto.plan_id} not found")

        if dto.subscription_id is not None:
            subscription = await self._session.get(Subscription, dto.subscription_id)
            if subscription is None:
                raise NotFoundError(f"Subscription with id={dto.subscription_id} not found")
            if subscription.user_id != user.id:
                raise PaymentError("Subscription does not belong to user")

        payment = Payment(
            user_id=user.id,
            plan_id=plan.id,
            subscription_id=dto.subscription_id,
            amount=plan.price,
            currency=plan.currency,
            provider=dto.provider,
            status=PaymentStatus.PENDING,
            raw_payload={},
        )
        self._session.add(payment)
        await self._session.flush()

        adapter = self._get_adapter(dto.provider)
        created = await adapter.create(payment, plan, user)

        payment.provider_payment_id = created.provider_payment_id
        payment.payment_url = created.payment_url
        payment.raw_payload = created.raw
        await self._session.flush()
        await self._session.refresh(payment)
        return payment

    async def get(self, payment_id: int) -> Payment:
        payment = await self._session.get(Payment, payment_id)
        if payment is None:
            raise NotFoundError(f"Payment with id={payment_id} not found")
        return payment

    async def handle_webhook(
        self,
        provider: PaymentProvider,
        body: bytes,
        headers: Mapping[str, str],
    ) -> Payment | None:
        adapter = self._get_adapter(provider)
        verified: WebhookVerificationResult = await adapter.verify_webhook(body, headers)

        result = await self._session.execute(
            select(Payment).where(
                Payment.provider == provider,
                Payment.provider_payment_id == verified.provider_payment_id,
            )
        )
        payment = result.scalar_one_or_none()
        if payment is None:
            return None

        payment.status = verified.status
        payment.raw_payload = verified.raw
        await self._session.flush()

        if verified.status == PaymentStatus.SUCCEEDED:
            await self._subscriptions.create_from_payment(payment)

        await self._session.refresh(payment)
        return payment
