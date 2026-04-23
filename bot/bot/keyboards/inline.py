"""Inline keyboards for plans, providers, subscriptions, etc."""

from __future__ import annotations

from collections.abc import Iterable

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from shared.enums import Locale, PaymentProvider
from shared.schemas import PlanOut, SubscriptionOut

from bot.i18n import Translator
from bot.utils.vpn_instructions import SUPPORTED_OSES


def plans_keyboard(plans: Iterable[PlanOut], t: Translator) -> InlineKeyboardMarkup:
    """Inline list of plans as ``plan:{id}`` callbacks."""
    rows: list[list[InlineKeyboardButton]] = []
    for plan in plans:
        traffic = (
            t("buy.traffic_unlimited")
            if plan.traffic_gb == 0
            else t("buy.traffic_gb", gb=plan.traffic_gb)
        )
        label = f"{plan.name} · {plan.duration_days}d · {traffic} · {plan.price} {plan.currency}"
        rows.append([InlineKeyboardButton(text=label, callback_data=f"plan:{plan.id}")])
    rows.append([InlineKeyboardButton(text=t("common.back"), callback_data="menu:main")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def providers_keyboard(plan_id: int, t: Translator) -> InlineKeyboardMarkup:
    """Payment provider picker for a specific plan."""
    providers = (
        (PaymentProvider.YOOKASSA, t("buy.provider.yookassa")),
        (PaymentProvider.CRYPTOBOT, t("buy.provider.cryptobot")),
        (PaymentProvider.TELEGRAM_STARS, t("buy.provider.stars")),
    )
    rows = [
        [InlineKeyboardButton(text=label, callback_data=f"pay:{plan_id}:{provider.value}")]
        for provider, label in providers
    ]
    rows.append([InlineKeyboardButton(text=t("common.back"), callback_data="buy:plans")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def payment_keyboard(
    payment_id: int,
    payment_url: str | None,
    t: Translator,
) -> InlineKeyboardMarkup:
    """Keyboard shown after a payment is created."""
    rows: list[list[InlineKeyboardButton]] = []
    if payment_url:
        rows.append([InlineKeyboardButton(text=t("buy.pay_button"), url=payment_url)])
    rows.append(
        [InlineKeyboardButton(text=t("buy.check_button"), callback_data=f"check:{payment_id}")],
    )
    rows.append([InlineKeyboardButton(text=t("common.back"), callback_data="menu:main")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def subscriptions_keyboard(
    subscriptions: Iterable[SubscriptionOut],
    t: Translator,
) -> InlineKeyboardMarkup:
    """List of user subscriptions with action buttons per item."""
    rows: list[list[InlineKeyboardButton]] = []
    for sub in subscriptions:
        rows.append(
            [
                InlineKeyboardButton(
                    text=t("subs.show_link"),
                    callback_data=f"sub_link:{sub.id}",
                ),
                InlineKeyboardButton(
                    text=t("subs.renew"),
                    callback_data=f"sub_renew:{sub.id}",
                ),
            ],
        )
    rows.append(
        [InlineKeyboardButton(text=t("subs.instructions"), callback_data="help:os")],
    )
    return InlineKeyboardMarkup(inline_keyboard=rows)


def help_os_keyboard(t: Translator) -> InlineKeyboardMarkup:
    """OS picker for the help section."""
    labels = {
        "android": t("help.os.android"),
        "ios": t("help.os.ios"),
        "windows": t("help.os.windows"),
        "macos": t("help.os.macos"),
    }
    rows = [
        [InlineKeyboardButton(text=labels[os_name], callback_data=f"help_os:{os_name}")]
        for os_name in SUPPORTED_OSES
    ]
    rows.append([InlineKeyboardButton(text=t("common.back"), callback_data="menu:main")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def language_keyboard(t: Translator) -> InlineKeyboardMarkup:
    """Language picker keyboard."""
    rows = [
        [
            InlineKeyboardButton(text="🇷🇺 Русский", callback_data=f"lang:{Locale.RU.value}"),
            InlineKeyboardButton(text="🇬🇧 English", callback_data=f"lang:{Locale.EN.value}"),
        ],
        [InlineKeyboardButton(text=t("common.back"), callback_data="menu:main")],
    ]
    return InlineKeyboardMarkup(inline_keyboard=rows)
