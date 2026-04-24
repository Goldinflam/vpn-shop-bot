"""Cross-cutting handlers: language picker + catch-all."""

from __future__ import annotations

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.types import CallbackQuery, Message
from shared.enums import Locale

from bot.filters import MenuButton
from bot.i18n import I18n, Translator
from bot.keyboards.inline import language_keyboard
from bot.keyboards.reply import main_menu
from bot.middlewares.i18n import LocaleStore

router = Router(name="common")


@router.message(Command("cancel"))
async def handle_cancel(message: Message, t: Translator) -> None:
    await message.answer(t("common.cancel"), reply_markup=main_menu(t))


@router.message(MenuButton("menu.language"))
async def maybe_open_language(message: Message, t: Translator) -> None:
    await message.answer(t("language.pick"), reply_markup=language_keyboard(t))


@router.callback_query(F.data.startswith("lang:"))
async def on_language_chosen(
    callback: CallbackQuery,
    locale_store: LocaleStore,
    i18n: I18n,
) -> None:
    if callback.data is None or callback.from_user is None:
        await callback.answer()
        return
    try:
        new_locale = Locale(callback.data.split(":", 1)[1])
    except ValueError:
        await callback.answer()
        return
    locale_store.set(callback.from_user.id, new_locale)
    new_t = i18n.translator(new_locale)
    if callback.message is not None and isinstance(callback.message, Message):
        await callback.message.answer(
            new_t("language.saved"),
            reply_markup=main_menu(new_t),
        )
    await callback.answer()
