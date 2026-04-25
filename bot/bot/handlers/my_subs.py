"""'My subscriptions' handler and follow-ups."""

from __future__ import annotations

import logging

from aiogram import F, Router
from aiogram.types import CallbackQuery, Message
from shared.schemas import SubscriptionRenew

from bot.api_client import BackendClient, BackendError
from bot.filters import MenuButton
from bot.i18n import Translator
from bot.keyboards.inline import subscriptions_keyboard

logger = logging.getLogger(__name__)

router = Router(name="my_subs")


@router.message(MenuButton("menu.my_subs"))
async def maybe_open_subs(
    message: Message,
    t: Translator,
    backend: BackendClient,
) -> None:
    """Trigger on the localized 'My subscriptions' button."""
    if message.from_user is None:
        return
    await _render_subs(message, message.from_user.id, t, backend)


async def _render_subs(
    message: Message,
    telegram_id: int,
    t: Translator,
    backend: BackendClient,
) -> None:
    try:
        subs = await backend.user_subscriptions(telegram_id)
    except BackendError as exc:
        logger.warning("user_subscriptions failed for %s: %s", telegram_id, exc)
        await message.answer(t("common.not_available"))
        return
    if not subs:
        await message.answer(t("subs.empty"))
        return
    lines = [t("subs.list_header")]
    for sub in subs:
        lines.append(
            t(
                "subs.item",
                id=sub.id,
                expires=sub.expires_at.date().isoformat(),
                status=sub.status.value,
            ),
        )
    await message.answer("\n".join(lines), reply_markup=subscriptions_keyboard(subs, t))


@router.callback_query(F.data.startswith("sub_link:"))
async def on_show_link(
    callback: CallbackQuery,
    t: Translator,
    backend: BackendClient,
) -> None:
    if callback.data is None:
        await callback.answer()
        return
    try:
        sub_id = int(callback.data.split(":", 1)[1])
    except (IndexError, ValueError):
        await callback.answer()
        return
    try:
        sub = await backend.get_subscription(sub_id)
    except BackendError as exc:
        logger.warning("get_subscription %s failed: %s", sub_id, exc)
        await callback.answer(t("common.not_available"), show_alert=True)
        return
    if callback.message is not None and isinstance(callback.message, Message):
        await callback.message.answer(
            t("subs.link_message", link=sub.vless_link),
            parse_mode="HTML",
        )
    await callback.answer()


@router.callback_query(F.data.startswith("sub_renew:"))
async def on_renew(
    callback: CallbackQuery,
    t: Translator,
    backend: BackendClient,
) -> None:
    if callback.data is None:
        await callback.answer()
        return
    try:
        sub_id = int(callback.data.split(":", 1)[1])
    except (IndexError, ValueError):
        await callback.answer()
        return
    try:
        sub = await backend.get_subscription(sub_id)
        payment = await backend.renew_subscription(
            sub_id,
            SubscriptionRenew(plan_id=sub.plan_id),
        )
    except BackendError as exc:
        logger.warning("renew %s failed: %s", sub_id, exc)
        await callback.answer(t("common.not_available"), show_alert=True)
        return
    if (
        callback.message is not None
        and isinstance(callback.message, Message)
        and payment.payment_url
    ):
        await callback.message.answer(
            f"{t('buy.invoice_ready')}\n{payment.payment_url}",
        )
    await callback.answer()
