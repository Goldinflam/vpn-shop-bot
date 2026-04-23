"""FSM states for the purchase flow."""

from __future__ import annotations

from aiogram.fsm.state import State, StatesGroup


class BuyFlow(StatesGroup):
    """State machine for the buy flow: plan -> provider -> payment."""

    choosing_plan = State()
    choosing_provider = State()
    awaiting_payment = State()


class BroadcastFlow(StatesGroup):
    """State machine for the admin /broadcast command."""

    awaiting_text = State()
