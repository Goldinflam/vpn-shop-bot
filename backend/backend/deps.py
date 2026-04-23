"""FastAPI dependencies — auth, DB sessions, service wiring."""

from __future__ import annotations

from collections.abc import AsyncIterator
from typing import Annotated

from fastapi import Depends, Header, HTTPException, status
from shared.contracts.http import HEADER_ADMIN_TOKEN, HEADER_BOT_TOKEN
from sqlalchemy.ext.asyncio import AsyncSession

from backend.config import Settings, get_settings
from backend.db import get_sessionmaker
from backend.services import (
    PaymentService,
    PlanService,
    SubscriptionService,
    UserService,
)
from backend.xui import get_xui_client


async def db_session() -> AsyncIterator[AsyncSession]:
    """Yield an ``AsyncSession`` bound to the current request, commit on success."""
    maker = get_sessionmaker()
    async with maker() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


SessionDep = Annotated[AsyncSession, Depends(db_session)]
SettingsDep = Annotated[Settings, Depends(get_settings)]


async def require_bot_token(
    settings: SettingsDep,
    x_bot_token: Annotated[str | None, Header(alias=HEADER_BOT_TOKEN)] = None,
) -> None:
    if not x_bot_token or x_bot_token != settings.bot_api_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="invalid_bot_token"
        )


async def require_admin_token(
    settings: SettingsDep,
    x_admin_token: Annotated[str | None, Header(alias=HEADER_ADMIN_TOKEN)] = None,
) -> None:
    if not x_admin_token or x_admin_token != settings.admin_api_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="invalid_admin_token"
        )


def get_user_service(session: SessionDep) -> UserService:
    return UserService(session)


def get_plan_service(session: SessionDep) -> PlanService:
    return PlanService(session)


def get_subscription_service(session: SessionDep) -> SubscriptionService:
    return SubscriptionService(session, get_xui_client())


def get_payment_service(
    session: SessionDep,
    subscription_service: Annotated[SubscriptionService, Depends(get_subscription_service)],
) -> PaymentService:
    return PaymentService(session, subscription_service)


UserServiceDep = Annotated[UserService, Depends(get_user_service)]
PlanServiceDep = Annotated[PlanService, Depends(get_plan_service)]
SubscriptionServiceDep = Annotated[SubscriptionService, Depends(get_subscription_service)]
PaymentServiceDep = Annotated[PaymentService, Depends(get_payment_service)]
