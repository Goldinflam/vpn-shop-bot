"""Subscription router."""

from __future__ import annotations

import io

import qrcode
from fastapi import APIRouter, Depends, Response
from shared.contracts.http import (
    SUBSCRIPTION_GET,
    SUBSCRIPTION_QR,
    SUBSCRIPTION_RENEW,
)
from shared.enums import PaymentProvider
from shared.schemas import (
    PaymentOut,
    SubscriptionOut,
    SubscriptionRenew,
)
from shared.schemas.payment import PaymentCreate

from backend.deps import (
    PaymentServiceDep,
    SessionDep,
    SubscriptionServiceDep,
    require_bot_token,
)
from backend.services.users import UserService

router = APIRouter(tags=["subscriptions"], dependencies=[Depends(require_bot_token)])


@router.get(SUBSCRIPTION_GET, response_model=SubscriptionOut)
async def get_subscription(
    subscription_id: int, service: SubscriptionServiceDep
) -> SubscriptionOut:
    sub = await service.get(subscription_id)
    return SubscriptionOut.model_validate(sub)


@router.post(SUBSCRIPTION_RENEW, response_model=PaymentOut)
async def renew_subscription(
    subscription_id: int,
    dto: SubscriptionRenew,
    session: SessionDep,
    subscription_service: SubscriptionServiceDep,
    payment_service: PaymentServiceDep,
) -> PaymentOut:
    sub = await subscription_service.get(subscription_id)
    user = await UserService(session).get_by_id(sub.user_id)

    create_dto = PaymentCreate(
        telegram_id=user.telegram_id,
        plan_id=dto.plan_id,
        provider=PaymentProvider.TEST,
        subscription_id=subscription_id,
    )
    payment = await payment_service.create(create_dto)
    return PaymentOut.model_validate(payment)


@router.get(SUBSCRIPTION_QR)
async def get_subscription_qr(
    subscription_id: int, service: SubscriptionServiceDep
) -> Response:
    sub = await service.get(subscription_id)
    img = qrcode.make(sub.vless_link)
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return Response(content=buf.getvalue(), media_type="image/png")
