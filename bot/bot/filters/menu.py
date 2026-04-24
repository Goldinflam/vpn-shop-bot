"""Filter that matches a single main-menu reply button by i18n key.

aiogram v3 filters run BEFORE inner middlewares, so the
:class:`~bot.i18n.Translator` isn't available in filter data (it is
injected by :class:`~bot.middlewares.i18n.I18nMiddleware`, which is an
inner middleware). An earlier version of this filter accepted ``t`` as
a kwarg and crashed every update with::

    TypeError: MenuButton.__call__() missing 1 required positional
    argument: 't'

Fix: resolve the set of acceptable labels at construction time from the
static i18n catalog — one label per supported locale — and compare
``message.text`` against that set. No runtime translator needed.
"""

from __future__ import annotations

from aiogram.filters import BaseFilter
from aiogram.types import Message

from bot.i18n.catalog import CATALOG


class MenuButton(BaseFilter):
    """Match a specific localized main-menu button by i18n key."""

    def __init__(self, key: str) -> None:
        self.key = key
        labels: set[str] = set()
        for locale_catalog in CATALOG.values():
            label = locale_catalog.get(key)
            if label:
                labels.add(label)
        self._labels = frozenset(labels)

    async def __call__(self, message: Message) -> bool:
        if not message.text:
            return False
        return message.text in self._labels
