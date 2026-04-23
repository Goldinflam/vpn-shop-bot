"""Per-OS VPN client installation instructions.

Texts are intentionally short; the goal is to provide a single Telegram
message per OS with deep links to recommended VLESS clients. Both ru and
en variants are included so the language middleware can pick one.
"""

from __future__ import annotations

from typing import Final

from shared.enums import Locale

# OS identifier → localized body with deep links.
_INSTRUCTIONS_RU: Final[dict[str, str]] = {
    "android": (
        "<b>Android</b>\n"
        "1. Установите v2rayNG: "
        "https://play.google.com/store/apps/details?id=com.v2ray.ang\n"
        "2. Откройте VLESS-ссылку или отсканируйте QR-код.\n"
        "3. Нажмите «Подключиться»."
    ),
    "ios": (
        "<b>iOS</b>\n"
        "1. Установите Happ или FoXray из App Store.\n"
        "2. Импортируйте VLESS-ссылку или QR-код.\n"
        "3. Разрешите VPN-конфигурацию и нажмите «Подключиться»."
    ),
    "windows": (
        "<b>Windows</b>\n"
        "1. Установите Hiddify: https://hiddify.com/\n"
        "2. Добавьте конфигурацию через VLESS-ссылку.\n"
        "3. Выберите сервер и нажмите «Подключиться»."
    ),
    "macos": (
        "<b>macOS</b>\n"
        "1. Установите FoXray или Hiddify из Mac App Store.\n"
        "2. Импортируйте VLESS-ссылку.\n"
        "3. Разрешите VPN-конфигурацию и подключитесь."
    ),
}

_INSTRUCTIONS_EN: Final[dict[str, str]] = {
    "android": (
        "<b>Android</b>\n"
        "1. Install v2rayNG: "
        "https://play.google.com/store/apps/details?id=com.v2ray.ang\n"
        "2. Open the VLESS link or scan the QR code.\n"
        "3. Tap Connect."
    ),
    "ios": (
        "<b>iOS</b>\n"
        "1. Install Happ or FoXray from the App Store.\n"
        "2. Import the VLESS link or QR code.\n"
        "3. Allow the VPN configuration and tap Connect."
    ),
    "windows": (
        "<b>Windows</b>\n"
        "1. Install Hiddify: https://hiddify.com/\n"
        "2. Add a configuration from the VLESS link.\n"
        "3. Pick the server and click Connect."
    ),
    "macos": (
        "<b>macOS</b>\n"
        "1. Install FoXray or Hiddify from the Mac App Store.\n"
        "2. Import the VLESS link.\n"
        "3. Allow the VPN configuration and connect."
    ),
}

SUPPORTED_OSES: Final[tuple[str, ...]] = ("android", "ios", "windows", "macos")


def get_instructions(os_name: str, locale: Locale) -> str:
    """Return the installation text for ``os_name`` in the given ``locale``.

    Unknown OS names fall back to the Android instructions (the most
    common platform) to avoid surfacing an empty message to the user.
    """
    catalog = _INSTRUCTIONS_RU if locale == Locale.RU else _INSTRUCTIONS_EN
    return catalog.get(os_name, catalog["android"])
