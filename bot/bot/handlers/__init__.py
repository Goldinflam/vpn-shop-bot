"""aiogram routers exposed by the bot."""

from aiogram import Router

from bot.handlers.admin import router as admin_router
from bot.handlers.buy import router as buy_router
from bot.handlers.common import router as common_router
from bot.handlers.help import router as help_router
from bot.handlers.my_subs import router as my_subs_router
from bot.handlers.start import router as start_router


def build_root_router() -> Router:
    """Compose the root router with all feature routers attached."""
    root = Router(name="root")
    root.include_router(start_router)
    root.include_router(buy_router)
    root.include_router(my_subs_router)
    root.include_router(help_router)
    root.include_router(admin_router)
    root.include_router(common_router)
    return root


__all__ = ["build_root_router"]
