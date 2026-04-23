"""Injects a :class:`Translator` into handler kwargs as ``t``.

Locale is resolved from an in-memory override (set via the language
picker) or from the Telegram user's ``language_code`` as a fallback.
"""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import Any

from aiogram import BaseMiddleware
from aiogram.types import TelegramObject, User
from shared.enums import Locale

from bot.i18n import I18n, resolve_locale


class LocaleStore:
    """Process-memory mapping of Telegram user id -> :class:`Locale`.

    Persisting the user's locale across restarts is the backend's job (via
    ``UserOut.locale``); this cache just avoids refetching on every update.
    """

    def __init__(self) -> None:
        self._locales: dict[int, Locale] = {}

    def get(self, user_id: int) -> Locale | None:
        return self._locales.get(user_id)

    def set(self, user_id: int, locale: Locale) -> None:
        self._locales[user_id] = locale


class I18nMiddleware(BaseMiddleware):
    """Resolve locale and inject ``t`` + ``locale`` into handler data."""

    def __init__(self, i18n: I18n, store: LocaleStore) -> None:
        self._i18n = i18n
        self._store = store

    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        user: User | None = data.get("event_from_user")
        locale: Locale
        if user is not None:
            cached = self._store.get(user.id)
            locale = cached or resolve_locale(user.language_code, self._i18n.default_locale)
        else:
            locale = self._i18n.default_locale
        data["locale"] = locale
        data["t"] = self._i18n.translator(locale)
        data["locale_store"] = self._store
        return await handler(event, data)
