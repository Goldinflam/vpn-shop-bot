"""Payment router."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Request
from shared.contracts.http import (
    PAYMENT_GET,
    PAYMENT_WEBHOOK,
    PAYMENTS_CREATE,
)
from shared.enums import PaymentProvider
from shared.schemas import PaymentCreate, PaymentOut

from backend.deps import PaymentServiceDep, require_bot_token

router = APIRouter(tags=["payments"])


@router.post(
    PAYMENTS_CREATE,
    response_model=PaymentOut,
    dependencies=[Depends(require_bot_token)],
)
async def create_payment(dto: PaymentCreate, service: PaymentServiceDep) -> PaymentOut:
    payment = await service.create(dto)
    return PaymentOut.model_validate(payment)


@router.get(
    PAYMENT_GET,
    response_model=PaymentOut,
    dependencies=[Depends(require_bot_token)],
)
async def get_payment(payment_id: int, service: PaymentServiceDep) -> PaymentOut:
    payment = await service.get(payment_id)
    return PaymentOut.model_validate(payment)


@router.post(PAYMENT_WEBHOOK)
async def payment_webhook(
    provider: PaymentProvider,
    request: Request,
    service: PaymentServiceDep,
) -> dict[str, str]:
    body = await request.body()
    headers = dict(request.headers.items())
    await service.handle_webhook(provider, body, headers)
    return {"status": "ok"}
