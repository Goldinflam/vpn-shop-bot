"""Buy flow: plan selection -> provider -> payment invoice."""

from __future__ import annotations

import logging

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message
from shared.enums import PaymentProvider, PaymentStatus
from shared.schemas import PaymentCreate

from bot.api_client import BackendClient, BackendError
from bot.i18n import Translator
from bot.keyboards.inline import (
    payment_keyboard,
    plans_keyboard,
    providers_keyboard,
)
from bot.states.buy import BuyFlow

logger = logging.getLogger(__name__)

router = Router(name="buy")


def _menu_buy_filter(value: str, t: Translator) -> bool:
    return value == t("menu.buy")


@router.message(F.text)
async def maybe_open_buy(
    message: Message,
    t: Translator,
    backend: BackendClient,
    state: FSMContext,
) -> None:
    """Fast-path: text equals the localized 'Buy' button."""
    if not message.text or message.text != t("menu.buy"):
        return
    await _open_plans(message, t, backend, state)


@router.callback_query(F.data == "buy:plans")
async def reopen_plans(
    callback: CallbackQuery,
    t: Translator,
    backend: BackendClient,
    state: FSMContext,
) -> None:
    if callback.message is not None and isinstance(callback.message, Message):
        await _open_plans(callback.message, t, backend, state)
    await callback.answer()


async def _open_plans(
    message: Message,
    t: Translator,
    backend: BackendClient,
    state: FSMContext,
) -> None:
    try:
        plans = await backend.list_plans()
    except BackendError as exc:
        logger.warning("list_plans failed: %s", exc)
        await message.answer(t("common.not_available"))
        return
    active = [plan for plan in plans if plan.is_active]
    if not active:
        await message.answer(t("buy.no_plans"))
        return
    await state.set_state(BuyFlow.choosing_plan)
    await message.answer(t("buy.pick_plan"), reply_markup=plans_keyboard(active, t))


@router.callback_query(F.data.startswith("plan:"))
async def on_plan_chosen(
    callback: CallbackQuery,
    t: Translator,
    backend: BackendClient,
    state: FSMContext,
) -> None:
    if callback.data is None:
        await callback.answer()
        return
    try:
        plan_id = int(callback.data.split(":", 1)[1])
    except (IndexError, ValueError):
        await callback.answer()
        return
    try:
        plan = await backend.get_plan(plan_id)
    except BackendError as exc:
        logger.warning("get_plan %s failed: %s", plan_id, exc)
        await callback.answer(t("common.not_available"), show_alert=True)
        return

    traffic = (
        t("buy.traffic_unlimited")
        if plan.traffic_gb == 0
        else t("buy.traffic_gb", gb=plan.traffic_gb)
    )
    card = t(
        "buy.plan_card",
        name=plan.name,
        duration_days=plan.duration_days,
        traffic=traffic,
        price=plan.price,
        currency=plan.currency.value,
    )
    await state.set_state(BuyFlow.choosing_provider)
    await state.update_data(plan_id=plan_id)
    if callback.message is not None and isinstance(callback.message, Message):
        await callback.message.answer(
            f"{card}\n\n{t('buy.pick_provider')}",
            reply_markup=providers_keyboard(plan_id, t),
            parse_mode="HTML",
        )
    await callback.answer()


@router.callback_query(F.data.startswith("pay:"))
async def on_provider_chosen(
    callback: CallbackQuery,
    t: Translator,
    backend: BackendClient,
    state: FSMContext,
) -> None:
    if callback.data is None or callback.from_user is None:
        await callback.answer()
        return
    try:
        _, plan_id_raw, provider_raw = callback.data.split(":", 2)
        plan_id = int(plan_id_raw)
        provider = PaymentProvider(provider_raw)
    except (ValueError, IndexError):
        await callback.answer()
        return

    try:
        payment = await backend.create_payment(
            PaymentCreate(
                telegram_id=callback.from_user.id,
                plan_id=plan_id,
                provider=provider,
            ),
        )
    except BackendError as exc:
        logger.warning("create_payment failed: %s", exc)
        await callback.answer(t("common.not_available"), show_alert=True)
        return

    await state.set_state(BuyFlow.awaiting_payment)
    await state.update_data(payment_id=payment.id)
    if callback.message is not None and isinstance(callback.message, Message):
        await callback.message.answer(
            t("buy.invoice_ready"),
            reply_markup=payment_keyboard(payment.id, payment.payment_url, t),
        )
    await callback.answer()


@router.callback_query(F.data.startswith("check:"))
async def on_check_payment(
    callback: CallbackQuery,
    t: Translator,
    backend: BackendClient,
) -> None:
    if callback.data is None:
        await callback.answer()
        return
    try:
        payment_id = int(callback.data.split(":", 1)[1])
    except (IndexError, ValueError):
        await callback.answer()
        return
    try:
        payment = await backend.get_payment(payment_id)
    except BackendError as exc:
        logger.warning("get_payment %s failed: %s", payment_id, exc)
        await callback.answer(t("common.not_available"), show_alert=True)
        return

    status_key = {
        PaymentStatus.PENDING: "buy.status_pending",
        PaymentStatus.SUCCEEDED: "buy.status_succeeded",
        PaymentStatus.FAILED: "buy.status_failed",
        PaymentStatus.CANCELED: "buy.status_failed",
    }.get(payment.status, "buy.status_pending")
    await callback.answer(t(status_key), show_alert=True)

    if payment.status == PaymentStatus.SUCCEEDED and payment.subscription_id is not None:
        try:
            sub = await backend.get_subscription(payment.subscription_id)
        except BackendError:
            return
        if callback.message is not None and isinstance(callback.message, Message):
            await callback.message.answer(
                t("subs.link_message", link=sub.vless_link),
                parse_mode="HTML",
            )
