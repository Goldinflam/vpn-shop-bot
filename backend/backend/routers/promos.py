"""Promo and trial router.

Endpoints:
    * ``POST /api/v1/trial/create`` — issue a default free trial (1 day / 2 GB)
      to the caller. One trial per ``telegram_id`` (DB-enforced).
    * ``POST /api/v1/promo/apply`` — redeem a promo code. Trial promos
      immediately provision a VLESS client and return the unified
      ``IssuedVpnOut`` shape; discount promos return the discount percent.

Both endpoints require the ``X-Bot-Token`` header.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends
from shared.contracts.http import PROMO_APPLY, TRIAL_CREATE
from shared.schemas import IssuedVpnOut, PromoApplyIn, PromoApplyOut, TrialCreateIn

from backend.deps import PromoServiceDep, require_bot_token

router = APIRouter(tags=["promo"], dependencies=[Depends(require_bot_token)])


@router.post(TRIAL_CREATE, response_model=IssuedVpnOut)
async def create_trial(dto: TrialCreateIn, service: PromoServiceDep) -> IssuedVpnOut:
    return await service.create_trial(dto.telegram_id)


@router.post(PROMO_APPLY, response_model=PromoApplyOut)
async def apply_promo(dto: PromoApplyIn, service: PromoServiceDep) -> PromoApplyOut:
    return await service.apply_promo(dto.telegram_id, dto.code)
