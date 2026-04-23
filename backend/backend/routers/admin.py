"""Admin router — plans CRUD, stats, broadcast."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from fastapi import APIRouter, Depends, status
from pydantic import BaseModel, Field
from shared.contracts.http import (
    ADMIN_BROADCAST,
    ADMIN_PLAN,
    ADMIN_PLANS,
    ADMIN_STATS,
)
from shared.enums import PaymentStatus, SubscriptionStatus
from shared.schemas import PlanCreate, PlanOut, PlanUpdate
from sqlalchemy import func, select

from backend.deps import (
    PlanServiceDep,
    SessionDep,
    require_admin_token,
    require_bot_token,
)
from backend.models import Payment, Subscription, User

router = APIRouter(
    tags=["admin"],
    dependencies=[Depends(require_bot_token), Depends(require_admin_token)],
)


class StatsOut(BaseModel):
    users_total: int
    subscriptions_active: int
    payments_succeeded: int
    revenue_succeeded: float
    generated_at: datetime


class BroadcastIn(BaseModel):
    text: str = Field(..., min_length=1)


class BroadcastOut(BaseModel):
    queued: int


@router.get(ADMIN_PLANS, response_model=list[PlanOut])
async def admin_list_plans(service: PlanServiceDep) -> list[PlanOut]:
    plans = await service.list_all()
    return [PlanOut.model_validate(p) for p in plans]


@router.post(ADMIN_PLANS, response_model=PlanOut, status_code=status.HTTP_201_CREATED)
async def admin_create_plan(dto: PlanCreate, service: PlanServiceDep) -> PlanOut:
    plan = await service.create(dto)
    return PlanOut.model_validate(plan)


@router.patch(ADMIN_PLAN, response_model=PlanOut)
async def admin_update_plan(
    plan_id: int, dto: PlanUpdate, service: PlanServiceDep
) -> PlanOut:
    plan = await service.update(plan_id, dto)
    return PlanOut.model_validate(plan)


@router.delete(ADMIN_PLAN, status_code=status.HTTP_204_NO_CONTENT)
async def admin_delete_plan(plan_id: int, service: PlanServiceDep) -> None:
    await service.delete(plan_id)


@router.get(ADMIN_STATS, response_model=StatsOut)
async def admin_stats(session: SessionDep) -> StatsOut:
    users_total = await _scalar(session, select(func.count(User.id)))
    subscriptions_active = await _scalar(
        session,
        select(func.count(Subscription.id)).where(
            Subscription.status == SubscriptionStatus.ACTIVE
        ),
    )
    payments_succeeded = await _scalar(
        session,
        select(func.count(Payment.id)).where(Payment.status == PaymentStatus.SUCCEEDED),
    )
    revenue_raw = await _scalar(
        session,
        select(func.coalesce(func.sum(Payment.amount), 0)).where(
            Payment.status == PaymentStatus.SUCCEEDED
        ),
    )
    return StatsOut(
        users_total=users_total,
        subscriptions_active=subscriptions_active,
        payments_succeeded=payments_succeeded,
        revenue_succeeded=float(revenue_raw),
        generated_at=datetime.now(UTC),
    )


@router.post(ADMIN_BROADCAST, response_model=BroadcastOut)
async def admin_broadcast(dto: BroadcastIn, session: SessionDep) -> BroadcastOut:
    # Backend does not speak directly to users — it returns the recipient
    # count so the bot can perform the actual broadcast.
    count = await _scalar(
        session, select(func.count(User.id)).where(User.is_banned.is_(False))
    )
    _ = dto.text  # reserved for future audit logging
    return BroadcastOut(queued=count)


async def _scalar(session: SessionDep, stmt: Any) -> int:
    result = await session.execute(stmt)
    value = result.scalar_one()
    if value is None:
        return 0
    return int(value)
