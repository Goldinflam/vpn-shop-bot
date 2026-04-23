"""Lightweight in-memory i18n for the bot.

We intentionally avoid the .po/.mo toolchain: the MVP only needs a handful
of strings in two locales, so a simple dict-backed catalog is easier to
review, ship and test than Babel artifacts. The public surface mirrors
what callers would expect from a typical i18n helper: pick a locale,
format by key, and fall back to the default locale for missing keys.
"""

from __future__ import annotations

from collections.abc import Mapping

from shared.enums import Locale

from bot.i18n.catalog import CATALOG

__all__ = ["I18n", "Translator", "resolve_locale"]


class Translator:
    """Resolver for a single locale bound to the catalog."""

    def __init__(self, locale: Locale, catalog: Mapping[Locale, Mapping[str, str]]) -> None:
        self.locale = locale
        self._catalog = catalog

    def get(self, key: str, /, **kwargs: object) -> str:
        """Return localized text for ``key`` formatted with ``kwargs``.

        Falls back to the Russian catalog (the project default) and finally
        to the raw key when a translation is missing.
        """
        messages = self._catalog.get(self.locale, {})
        template = messages.get(key)
        if template is None:
            template = self._catalog[Locale.RU].get(key, key)
        if not kwargs:
            return template
        return template.format(**kwargs)

    __call__ = get


class I18n:
    """Factory for per-request :class:`Translator` instances."""

    def __init__(
        self,
        default_locale: Locale = Locale.RU,
        catalog: Mapping[Locale, Mapping[str, str]] | None = None,
    ) -> None:
        self.default_locale = default_locale
        self._catalog = catalog or CATALOG

    def translator(self, locale: Locale | None = None) -> Translator:
        return Translator(locale or self.default_locale, self._catalog)


def resolve_locale(language_code: str | None, default: Locale = Locale.RU) -> Locale:
    """Pick a supported :class:`Locale` based on a Telegram language code."""
    if not language_code:
        return default
    code = language_code.lower().split("-")[0]
    if code in {"ru", "uk", "be", "kk"}:
        return Locale.RU
    if code == "en":
        return Locale.EN
    return default
