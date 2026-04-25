"""Plan service — CRUD for tariff plans."""

from __future__ import annotations

from shared.contracts.errors import NotFoundError
from shared.schemas import PlanCreate, PlanUpdate
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.models import Plan


class PlanService:
    """Business logic for ``Plan`` entities."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def list_active(self) -> list[Plan]:
        result = await self._session.execute(
            select(Plan).where(Plan.is_active.is_(True)).order_by(Plan.sort_order, Plan.id)
        )
        return list(result.scalars().all())

    async def list_all(self) -> list[Plan]:
        result = await self._session.execute(select(Plan).order_by(Plan.sort_order, Plan.id))
        return list(result.scalars().all())

    async def get(self, plan_id: int) -> Plan:
        plan = await self._session.get(Plan, plan_id)
        if plan is None:
            raise NotFoundError(f"Plan with id={plan_id} not found")
        return plan

    async def create(self, dto: PlanCreate) -> Plan:
        plan = Plan(
            name=dto.name,
            description=dto.description,
            duration_days=dto.duration_days,
            traffic_gb=dto.traffic_gb,
            price=dto.price,
            currency=dto.currency,
            is_active=dto.is_active,
            sort_order=dto.sort_order,
        )
        self._session.add(plan)
        await self._session.flush()
        await self._session.refresh(plan)
        return plan

    async def update(self, plan_id: int, dto: PlanUpdate) -> Plan:
        plan = await self.get(plan_id)
        data = dto.model_dump(exclude_unset=True)
        if "name" in data:
            plan.name = data["name"]
        if "description" in data:
            plan.description = data["description"]
        if "duration_days" in data:
            plan.duration_days = data["duration_days"]
        if "traffic_gb" in data:
            plan.traffic_gb = data["traffic_gb"]
        if "price" in data:
            plan.price = data["price"]
        if "currency" in data:
            plan.currency = data["currency"]
        if "is_active" in data:
            plan.is_active = data["is_active"]
        if "sort_order" in data:
            plan.sort_order = data["sort_order"]
        await self._session.flush()
        await self._session.refresh(plan)
        return plan

    async def delete(self, plan_id: int) -> None:
        plan = await self.get(plan_id)
        await self._session.delete(plan)
        await self._session.flush()
