"""Free-trial handler: one-tap "🚀 Попробовать бесплатно"."""

from __future__ import annotations

import logging

from aiogram import Router
from aiogram.types import Message

from bot.api_client import BackendClient, BackendError
from bot.filters import MenuButton
from bot.i18n import Translator
from bot.utils.happ import send_issued_vpn

logger = logging.getLogger(__name__)

router = Router(name="trial")


@router.message(MenuButton("menu.trial"))
async def maybe_start_trial(
    message: Message,
    t: Translator,
    backend: BackendClient,
) -> None:
    """Fast-path: text equals the localized "Try for free" button."""
    if message.from_user is None:
        return
    await message.answer(t("trial.intro"))
    logger.info("trial.create starting for tg_id=%s", message.from_user.id)
    try:
        issued = await backend.create_trial(message.from_user.id)
        logger.info(
            "trial.create succeeded for tg_id=%s sub_id=%s",
            message.from_user.id,
            issued.subscription.id,
        )
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
        await message.answer(
            f"{t('trial.failed')}\n<code>{_truncate(detail)}</code>",
            parse_mode="HTML",
        )
        return
    except Exception as exc:  # noqa: BLE001 — surface parsing / unexpected errors
        logger.exception("create_trial unexpected error for tg_id=%s", message.from_user.id)
        await message.answer(
            f"{t('trial.failed')}\n<code>{_truncate(str(exc))}</code>",
            parse_mode="HTML",
        )
        return
    try:
        await send_issued_vpn(message, issued, t)
    except Exception as exc:  # noqa: BLE001 — VPN issued, but rendering failed
        logger.exception(
            "send_issued_vpn failed for tg_id=%s — client IS created, rendering only failed",
            message.from_user.id,
        )
        await message.answer(
            "VPN выдан, но не удалось отрендерить кнопки. Вот ваша ссылка:\n"
            f"<code>{issued.vless_link}</code>\n\n<i>{_truncate(str(exc))}</i>",
            parse_mode="HTML",
            disable_web_page_preview=True,
        )


def _truncate(text: str, limit: int = 400) -> str:
    """Truncate free-form error text so the Telegram message stays under 4096 chars."""
    if len(text) <= limit:
        return text
    return text[: limit - 1] + "…"
