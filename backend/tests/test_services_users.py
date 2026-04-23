"""Tests for ``UserService``."""

from __future__ import annotations

import pytest
from backend.services.users import UserService
from shared.contracts.errors import NotFoundError
from shared.enums import Locale
from shared.schemas import UserUpsert
from sqlalchemy.ext.asyncio import AsyncSession


async def test_upsert_creates_user(session: AsyncSession) -> None:
    service = UserService(session)
    user = await service.upsert(
        UserUpsert(telegram_id=42, username="bob", first_name="Bob", language_code="en")
    )
    assert user.telegram_id == 42
    assert user.locale == Locale.EN


async def test_upsert_updates_existing_user(session: AsyncSession) -> None:
    service = UserService(session)
    await service.upsert(UserUpsert(telegram_id=42, username="bob"))
    user = await service.upsert(UserUpsert(telegram_id=42, username="bobby"))
    assert user.username == "bobby"


async def test_get_by_telegram_id_missing(session: AsyncSession) -> None:
    service = UserService(session)
    with pytest.raises(NotFoundError):
        await service.get_by_telegram_id(9999)


async def test_get_by_id(session: AsyncSession) -> None:
    service = UserService(session)
    created = await service.upsert(UserUpsert(telegram_id=42))
    fetched = await service.get_by_id(created.id)
    assert fetched.id == created.id


def test_resolve_locale_defaults() -> None:
    from backend.services.users import _resolve_locale

    assert _resolve_locale(None) == Locale.RU
    assert _resolve_locale("ru-RU") == Locale.RU
    assert _resolve_locale("EN") == Locale.EN
    assert _resolve_locale("fr") == Locale.RU
