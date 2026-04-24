"""Filter that matches a single localized reply-keyboard button.

Previously every menu handler used ``@router.message(F.text)`` and
early-returned inside the body when the text didn't match. In aiogram v3
that is a bug: once a filter matches (``F.text`` matches any text), the
event is considered handled and propagation to the next router stops —
even if the handler itself does nothing. This broke every menu button
except the first one registered ("🚀 Попробовать бесплатно").

:class:`MenuButton` resolves the localized label per request through the
injected :class:`~bot.i18n.Translator` and returns ``True`` only when the
message text matches it exactly, so non-matching messages cleanly fall
through to the next router.
"""

from __future__ import annotations

from aiogram.filters import BaseFilter
from aiogram.types import Message

from bot.i18n import Translator


class MenuButton(BaseFilter):
    """Match a specific localized main-menu button by i18n key."""

    def __init__(self, key: str) -> None:
        self.key = key

    async def __call__(self, message: Message, t: Translator) -> bool:
        if not message.text:
            return False
        return message.text == t(self.key)
