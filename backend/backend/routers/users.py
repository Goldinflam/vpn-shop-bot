"""User router."""

from __future__ import annotations

from fastapi import APIRouter, Depends
from shared.contracts.http import USER_GET, USER_SUBSCRIPTIONS, USERS_UPSERT
from shared.schemas import SubscriptionOut, UserOut, UserUpsert

from backend.deps import (
    SubscriptionServiceDep,
    UserServiceDep,
    require_bot_token,
)

router = APIRouter(tags=["users"], dependencies=[Depends(require_bot_token)])


@router.post(USERS_UPSERT, response_model=UserOut)
async def upsert_user(dto: UserUpsert, service: UserServiceDep) -> UserOut:
    user = await service.upsert(dto)
    return UserOut.model_validate(user)


@router.get(USER_GET, response_model=UserOut)
async def get_user(telegram_id: int, service: UserServiceDep) -> UserOut:
    user = await service.get_by_telegram_id(telegram_id)
    return UserOut.model_validate(user)


@router.get(USER_SUBSCRIPTIONS, response_model=list[SubscriptionOut])
async def list_user_subscriptions(
    telegram_id: int,
    user_service: UserServiceDep,
    subscription_service: SubscriptionServiceDep,
) -> list[SubscriptionOut]:
    user = await user_service.get_by_telegram_id(telegram_id)
    subs = await subscription_service.list_for_user(user.id)
    return [SubscriptionOut.model_validate(s) for s in subs]
