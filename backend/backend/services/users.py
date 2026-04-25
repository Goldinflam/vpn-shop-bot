"""User service."""

from __future__ import annotations

from shared.contracts.errors import NotFoundError
from shared.enums import Locale
from shared.schemas import UserUpsert
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.models import User

_LOCALE_MAP: dict[str, Locale] = {"ru": Locale.RU, "en": Locale.EN}


class UserService:
    """Business logic for ``User`` entities."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def upsert(self, dto: UserUpsert) -> User:
        """Create or update a user by ``telegram_id``."""
        result = await self._session.execute(
            select(User).where(User.telegram_id == dto.telegram_id)
        )
        user = result.scalar_one_or_none()

        locale = _resolve_locale(dto.language_code)

        if user is None:
            user = User(
                telegram_id=dto.telegram_id,
                username=dto.username,
                first_name=dto.first_name,
                last_name=dto.last_name,
                locale=locale,
            )
            self._session.add(user)
        else:
            user.username = dto.username
            user.first_name = dto.first_name
            user.last_name = dto.last_name
            user.locale = locale

        await self._session.flush()
        await self._session.refresh(user)
        return user

    async def get_by_telegram_id(self, telegram_id: int) -> User:
        result = await self._session.execute(select(User).where(User.telegram_id == telegram_id))
        user = result.scalar_one_or_none()
        if user is None:
            raise NotFoundError(f"User with telegram_id={telegram_id} not found")
        return user

    async def get_by_id(self, user_id: int) -> User:
        user = await self._session.get(User, user_id)
        if user is None:
            raise NotFoundError(f"User with id={user_id} not found")
        return user


def _resolve_locale(language_code: str | None) -> Locale:
    if language_code is None:
        return Locale.RU
    short = language_code.split("-", 1)[0].lower()
    return _LOCALE_MAP.get(short, Locale.RU)
