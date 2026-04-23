"""Middleware that upserts the Telegram user into the backend on every update.

Keeps backend's user table in sync with Telegram (username changes, new
first names, language changes). Injects the backend-side ``UserOut`` into
handler data as ``backend_user`` when available.
"""

from __future__ import annotations

import logging
from collections.abc import Awaitable, Callable
from typing import Any

from aiogram import BaseMiddleware
from aiogram.types import TelegramObject, User
from shared.schemas import UserUpsert

from bot.api_client import BackendClient, BackendError

logger = logging.getLogger(__name__)


class UserUpsertMiddleware(BaseMiddleware):
    """POST /users for every inbound update carrying a Telegram user."""

    def __init__(self, client: BackendClient) -> None:
        self._client = client

    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        user: User | None = data.get("event_from_user")
        if user is not None:
            try:
                backend_user = await self._client.upsert_user(
                    UserUpsert(
                        telegram_id=user.id,
                        username=user.username,
                        first_name=user.first_name,
                        last_name=user.last_name,
                        language_code=user.language_code,
                    ),
                )
                data["backend_user"] = backend_user
            except BackendError as exc:
                logger.warning("upsert_user failed for %s: %s", user.id, exc)
                data["backend_user"] = None
        data["backend"] = self._client
        return await handler(event, data)
