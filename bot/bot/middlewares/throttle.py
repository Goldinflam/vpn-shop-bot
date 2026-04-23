"""Very small per-user throttle to smooth out bursts of messages."""

from __future__ import annotations

import time
from collections.abc import Awaitable, Callable
from typing import Any

from aiogram import BaseMiddleware
from aiogram.types import TelegramObject, User


class ThrottleMiddleware(BaseMiddleware):
    """Drops updates from a user arriving faster than ``rate`` per second."""

    def __init__(self, rate: float = 0.3) -> None:
        self._rate = rate
        self._last_seen: dict[int, float] = {}

    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        user: User | None = data.get("event_from_user")
        if user is not None:
            now = time.monotonic()
            last = self._last_seen.get(user.id, 0.0)
            if now - last < self._rate:
                return None
            self._last_seen[user.id] = now
        return await handler(event, data)
