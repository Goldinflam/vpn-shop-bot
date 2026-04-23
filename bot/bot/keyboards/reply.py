"""Reply keyboards (main menu, etc.)."""

from __future__ import annotations

from aiogram.types import KeyboardButton, ReplyKeyboardMarkup

from bot.i18n import Translator


def main_menu(t: Translator) -> ReplyKeyboardMarkup:
    """Build the main menu keyboard localized with ``t``."""
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text=t("menu.buy")), KeyboardButton(text=t("menu.my_subs"))],
            [KeyboardButton(text=t("menu.help")), KeyboardButton(text=t("menu.language"))],
        ],
        resize_keyboard=True,
    )
