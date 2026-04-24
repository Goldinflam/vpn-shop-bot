"""Support handler: shows contact link to @Hael_support."""

from __future__ import annotations

from aiogram import Router
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, Message

from bot.filters import MenuButton
from bot.i18n import Translator

router = Router(name="support")

SUPPORT_URL = "https://t.me/Hael_support"


@router.message(MenuButton("menu.support"))
async def handle_support(message: Message, t: Translator) -> None:
    kb = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=t("support.open_chat"), url=SUPPORT_URL)],
        ],
    )
    await message.answer(t("support.message"), reply_markup=kb)
