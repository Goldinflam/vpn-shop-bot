"""Plan router."""

from __future__ import annotations

from fastapi import APIRouter, Depends
from shared.contracts.http import PLAN_GET, PLANS_LIST
from shared.schemas import PlanOut

from backend.deps import PlanServiceDep, require_bot_token

router = APIRouter(tags=["plans"], dependencies=[Depends(require_bot_token)])


@router.get(PLANS_LIST, response_model=list[PlanOut])
async def list_plans(service: PlanServiceDep) -> list[PlanOut]:
    plans = await service.list_active()
    return [PlanOut.model_validate(p) for p in plans]


@router.get(PLAN_GET, response_model=PlanOut)
async def get_plan(plan_id: int, service: PlanServiceDep) -> PlanOut:
    plan = await service.get(plan_id)
    return PlanOut.model_validate(plan)
