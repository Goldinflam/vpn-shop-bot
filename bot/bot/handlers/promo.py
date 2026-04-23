"""Promo-code entry flow: prompt → apply → react (trial or discount)."""

from __future__ import annotations

import logging

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import Message

from bot.api_client import BackendClient, BackendError
from bot.i18n import Translator
from bot.states.promo import PromoFlow
from bot.utils.happ import send_issued_vpn

logger = logging.getLogger(__name__)

router = Router(name="promo")

_ERROR_CODE_TO_KEY: dict[str, str] = {
    "promo_not_found": "promo.not_found",
    "promo_expired": "promo.expired",
    "promo_exhausted": "promo.exhausted",
    "promo_already_used": "promo.already_used",
    "trial_already_claimed": "promo.trial_claimed",
}


@router.message(F.text)
async def maybe_open_promo(
    message: Message,
    t: Translator,
    state: FSMContext,
) -> None:
    """Fast-path: text equals the localized "Enter promo code" button."""
    if not message.text or message.text != t("menu.promo"):
        return
    await state.set_state(PromoFlow.awaiting_code)
    await message.answer(t("promo.prompt"))


@router.message(PromoFlow.awaiting_code, Command("cancel"))
async def cancel_promo(
    message: Message,
    t: Translator,
    state: FSMContext,
) -> None:
    await state.clear()
    await message.answer(t("promo.cancelled"))


@router.message(PromoFlow.awaiting_code, F.text)
async def on_promo_code(
    message: Message,
    t: Translator,
    state: FSMContext,
    backend: BackendClient,
) -> None:
    if not message.text or message.from_user is None:
        return
    code = message.text.strip()
    if not code or code.startswith("/"):
        await message.answer(t("promo.prompt"))
        return

    await state.clear()
    try:
        result = await backend.apply_promo(message.from_user.id, code)
    except BackendError as exc:
        logger.info("apply_promo failed: %s", exc)
        key = _map_error_key(exc)
        await message.answer(t(key))
        return

    if result.is_trial and result.issued is not None:
        await message.answer(t("promo.applied_trial"))
        await send_issued_vpn(message, result.issued, t)
        return

    if result.discount_percent is not None:
        await message.answer(t("promo.applied_discount", percent=result.discount_percent))
        return

    # Shouldn't happen — defensive branch.
    await message.answer(t("promo.error"))


def _map_error_key(exc: BackendError) -> str:
    """Derive an i18n key from the backend's structured error ``code``."""
    message = getattr(exc, "message", "") or str(exc)
    # backend uses JSON like {"code": "...", "detail": "..."}; error messages
    # from the API client are the ``detail`` string, not the code — so we
    # fall back to HTTP-status-based heuristics here.
    status_code = getattr(exc, "status_code", 0)
    if status_code == 404:
        return "promo.not_found"
    if status_code == 410:
        return "promo.expired"
    if status_code == 409:
        if "trial" in message.lower():
            return "promo.trial_claimed"
        return "promo.already_used"
    return "promo.error"
