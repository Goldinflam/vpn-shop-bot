"""Admin commands: /stats and /broadcast."""

from __future__ import annotations

import logging

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import Message

from bot.api_client import BackendClient, BackendError
from bot.config import Settings
from bot.i18n import Translator
from bot.states.buy import BroadcastFlow

logger = logging.getLogger(__name__)

router = Router(name="admin")


def _is_admin(user_id: int, settings: Settings) -> bool:
    return user_id in settings.admin_ids


@router.message(Command("stats"))
async def handle_stats(
    message: Message,
    t: Translator,
    backend: BackendClient,
    settings: Settings,
) -> None:
    if message.from_user is None or not _is_admin(message.from_user.id, settings):
        await message.answer(t("admin.not_allowed"))
        return
    try:
        stats = await backend.admin_stats()
    except BackendError as exc:
        logger.warning("admin_stats failed: %s", exc)
        await message.answer(t("common.not_available"))
        return
    lines = [t("admin.stats_header")]
    for key, value in stats.items():
        lines.append(f"• <b>{key}</b>: {value}")
    await message.answer("\n".join(lines), parse_mode="HTML")


@router.message(Command("broadcast"))
async def handle_broadcast_start(
    message: Message,
    t: Translator,
    settings: Settings,
    state: FSMContext,
) -> None:
    if message.from_user is None or not _is_admin(message.from_user.id, settings):
        await message.answer(t("admin.not_allowed"))
        return
    await state.set_state(BroadcastFlow.awaiting_text)
    await message.answer(t("admin.broadcast.prompt"))


@router.message(BroadcastFlow.awaiting_text, Command("cancel"))
async def handle_broadcast_cancel(
    message: Message,
    t: Translator,
    state: FSMContext,
) -> None:
    await state.clear()
    await message.answer(t("admin.broadcast.cancelled"))


@router.message(BroadcastFlow.awaiting_text, F.text)
async def handle_broadcast_text(
    message: Message,
    t: Translator,
    backend: BackendClient,
    state: FSMContext,
) -> None:
    if not message.text:
        return
    await state.clear()
    try:
        result = await backend.admin_broadcast(message.text)
    except BackendError as exc:
        logger.warning("admin_broadcast failed: %s", exc)
        await message.answer(t("common.not_available"))
        return
    count = int(result.get("recipients", 0))
    await message.answer(t("admin.broadcast.done", count=count))
