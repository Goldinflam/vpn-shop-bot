"""Tests for ``PlanService``."""

from __future__ import annotations

from decimal import Decimal

import pytest
from backend.services.plans import PlanService
from shared.contracts.errors import NotFoundError
from shared.schemas import PlanCreate, PlanUpdate
from sqlalchemy.ext.asyncio import AsyncSession


async def test_create_and_list_active(session: AsyncSession) -> None:
    service = PlanService(session)
    created = await service.create(
        PlanCreate(name="1m", duration_days=30, traffic_gb=0, price=Decimal("100"))
    )
    inactive = await service.create(
        PlanCreate(
            name="old",
            duration_days=30,
            traffic_gb=0,
            price=Decimal("50"),
            is_active=False,
        )
    )
    active = await service.list_active()
    all_plans = await service.list_all()
    assert created.id in {p.id for p in active}
    assert inactive.id not in {p.id for p in active}
    assert len(all_plans) == 2


async def test_update_plan(session: AsyncSession) -> None:
    service = PlanService(session)
    plan = await service.create(
        PlanCreate(name="1m", duration_days=30, traffic_gb=0, price=Decimal("100"))
    )
    updated = await service.update(plan.id, PlanUpdate(price=Decimal("150")))
    assert updated.price == Decimal("150.00")


async def test_delete_plan(session: AsyncSession) -> None:
    service = PlanService(session)
    plan = await service.create(
        PlanCreate(name="1m", duration_days=30, traffic_gb=0, price=Decimal("100"))
    )
    await service.delete(plan.id)
    with pytest.raises(NotFoundError):
        await service.get(plan.id)


async def test_get_missing(session: AsyncSession) -> None:
    service = PlanService(session)
    with pytest.raises(NotFoundError):
        await service.get(9999)
