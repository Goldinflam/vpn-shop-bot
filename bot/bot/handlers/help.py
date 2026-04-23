"""Help / instruction flow."""

from __future__ import annotations

from aiogram import F, Router
from aiogram.types import CallbackQuery, Message
from shared.enums import Locale

from bot.i18n import Translator
from bot.keyboards.inline import help_os_keyboard
from bot.utils.vpn_instructions import get_instructions

router = Router(name="help")


@router.message(F.text)
async def maybe_open_help(message: Message, t: Translator) -> None:
    if not message.text or message.text != t("menu.help"):
        return
    await message.answer(t("help.pick_os"), reply_markup=help_os_keyboard(t))


@router.callback_query(F.data == "help:os")
async def show_os_picker(callback: CallbackQuery, t: Translator) -> None:
    if callback.message is not None and isinstance(callback.message, Message):
        await callback.message.answer(t("help.pick_os"), reply_markup=help_os_keyboard(t))
    await callback.answer()


@router.callback_query(F.data.startswith("help_os:"))
async def on_os_picked(callback: CallbackQuery, t: Translator, locale: Locale) -> None:
    if callback.data is None:
        await callback.answer()
        return
    os_name = callback.data.split(":", 1)[1]
    text = get_instructions(os_name, locale)
    if callback.message is not None and isinstance(callback.message, Message):
        await callback.message.answer(text, parse_mode="HTML")
    await callback.answer()
