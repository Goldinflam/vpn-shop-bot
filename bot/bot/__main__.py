"""Entry point: ``python -m bot`` starts long polling."""

from __future__ import annotations

import asyncio
import logging

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage

from bot.api_client import BackendClient
from bot.config import Settings, get_settings
from bot.handlers import build_root_router
from bot.i18n import I18n
from bot.middlewares.i18n import I18nMiddleware, LocaleStore
from bot.middlewares.throttle import ThrottleMiddleware
from bot.middlewares.user_upsert import UserUpsertMiddleware

logger = logging.getLogger(__name__)


def _build_dispatcher(
    settings: Settings,
    backend: BackendClient,
    i18n: I18n,
    locale_store: LocaleStore,
) -> Dispatcher:
    dispatcher = Dispatcher(storage=MemoryStorage())
    dispatcher["settings"] = settings
    dispatcher["i18n"] = i18n
    dispatcher["locale_store"] = locale_store

    throttle = ThrottleMiddleware()
    locale_mw = I18nMiddleware(i18n, locale_store)
    upsert_mw = UserUpsertMiddleware(backend)

    for observer in (dispatcher.message, dispatcher.callback_query):
        observer.middleware(throttle)
        observer.middleware(locale_mw)
        observer.middleware(upsert_mw)

    dispatcher.include_router(build_root_router())
    return dispatcher


async def run() -> None:
    settings = get_settings()
    logging.basicConfig(
        level=settings.log_level,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )

    bot = Bot(
        token=settings.bot_token.get_secret_value(),
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )
    backend = BackendClient(
        base_url=settings.backend_url,
        bot_token=settings.bot_api_token.get_secret_value(),
        admin_token=(
            settings.admin_api_token.get_secret_value() if settings.admin_api_token else None
        ),
    )
    i18n = I18n(default_locale=settings.default_locale)
    locale_store = LocaleStore()

    dispatcher = _build_dispatcher(settings, backend, i18n, locale_store)

    try:
        await dispatcher.start_polling(bot)
    finally:
        await backend.aclose()
        await bot.session.close()


def main() -> None:
    asyncio.run(run())


if __name__ == "__main__":
    main()
