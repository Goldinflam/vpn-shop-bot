"""FSM states for the promo-code flow."""

from __future__ import annotations

from aiogram.fsm.state import State, StatesGroup


class PromoFlow(StatesGroup):
    """State machine for the promo flow: prompt -> enter code."""

    awaiting_code = State()
