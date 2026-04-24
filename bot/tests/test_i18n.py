"""Tests for the lightweight i18n helper."""

from __future__ import annotations

import pytest
from bot.i18n import I18n, resolve_locale
from shared.enums import Locale


def test_translator_picks_locale() -> None:
    i18n = I18n(default_locale=Locale.RU)
    assert i18n.translator(Locale.RU)("menu.buy") == "💰 Тарифы"
    assert i18n.translator(Locale.EN)("menu.buy") == "💰 Plans"
    assert i18n.translator(Locale.RU)("menu.trial") == "🚀 Попробовать бесплатно"
    assert i18n.translator(Locale.RU)("menu.promo") == "🎁 Ввести промокод"


def test_translator_formats_placeholders() -> None:
    i18n = I18n(default_locale=Locale.RU)
    text = i18n.translator(Locale.RU)("start.greeting", name="Ваня")
    assert "Ваня" in text


def test_missing_key_returns_key() -> None:
    i18n = I18n(default_locale=Locale.RU)
    assert i18n.translator(Locale.RU)("nope.missing") == "nope.missing"


@pytest.mark.parametrize(
    ("language_code", "expected"),
    [
        ("ru", Locale.RU),
        ("ru-RU", Locale.RU),
        ("en", Locale.EN),
        ("en-US", Locale.EN),
        ("uk", Locale.RU),
        ("fr", Locale.RU),
        (None, Locale.RU),
    ],
)
def test_resolve_locale(language_code: str | None, expected: Locale) -> None:
    assert resolve_locale(language_code, default=Locale.RU) == expected
