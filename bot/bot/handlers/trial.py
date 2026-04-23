"""Free-trial handler: one-tap "🚀 Попробовать бесплатно"."""

from __future__ import annotations

import logging

from aiogram import F, Router
from aiogram.types import Message

from bot.api_client import BackendClient, BackendError
from bot.i18n import Translator
from bot.utils.happ import send_issued_vpn

logger = logging.getLogger(__name__)

router = Router(name="trial")


@router.message(F.text)
async def maybe_start_trial(
    message: Message,
    t: Translator,
    backend: BackendClient,
) -> None:
    """Fast-path: text equals the localized "Try for free" button."""
    if not message.text or message.text != t("menu.trial"):
        return
    if message.from_user is None:
        return
    await message.answer(t("trial.intro"))
    try:
        issued = await backend.create_trial(message.from_user.id)
    except BackendError as exc:
        logger.warning(
            "create_trial failed for tg_id=%s: status=%s detail=%s",
            message.from_user.id,
            getattr(exc, "status_code", 0),
            getattr(exc, "message", ""),
        )
        if getattr(exc, "status_code", 0) == 409:
            await message.answer(t("trial.already_claimed"))
            return
        detail = getattr(exc, "message", "") or str(exc)
        await message.answer(f"{t('trial.failed')}\n<code>{detail}</code>", parse_mode="HTML")
        return
    await send_issued_vpn(message, issued, t)
