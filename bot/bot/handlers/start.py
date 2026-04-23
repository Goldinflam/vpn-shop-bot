"""/start handler and main-menu entry points."""

from __future__ import annotations

from aiogram import F, Router
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from bot.i18n import Translator
from bot.keyboards.reply import main_menu

router = Router(name="start")


@router.message(CommandStart())
async def handle_start(message: Message, t: Translator, state: FSMContext) -> None:
    await state.clear()
    name = message.from_user.first_name if message.from_user else "friend"
    await message.answer(
        t("start.greeting", name=name),
        reply_markup=main_menu(t),
    )


@router.callback_query(F.data == "menu:main")
async def back_to_main(callback: CallbackQuery, t: Translator, state: FSMContext) -> None:
    await state.clear()
    if callback.message is not None:
        name = callback.from_user.first_name or "friend"
        await callback.message.answer(
            t("start.greeting", name=name),
            reply_markup=main_menu(t),
        )
    await callback.answer()
