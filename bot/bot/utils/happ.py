"""Helpers for sending issued-VPN messages with Happ deep links.

Every action that hands a user a working VLESS client — paid purchase,
trial, promo — surfaces the same three-button UI:

* "🚀 Подключиться" — ``happ://import-sub?url=...``
* "🔄 Открыть подписку" — opens the raw subscription URL in the browser
* "📥 Скачать Happ" — takes the user to the Happ download page

Plus a text fallback with the VLESS link and a QR-code image.
"""

from __future__ import annotations

import base64
from collections.abc import Sequence
from typing import Final

from aiogram.types import (
    BufferedInputFile,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    Message,
)
from shared.schemas import IssuedVpnOut

from bot.i18n import Translator

HAPP_DOWNLOAD_URL: Final[str] = "https://happ.su/en/"


def happ_buttons(issued: IssuedVpnOut, t: Translator) -> InlineKeyboardMarkup:
    """Build the inline keyboard with Happ connect/fallback/download buttons."""
    rows: list[list[InlineKeyboardButton]] = [
        [
            InlineKeyboardButton(
                text=t("vpn.happ_connect"),
                url=issued.happ_import_url,
            ),
        ],
    ]
    if issued.subscription_url:
        rows.append(
            [
                InlineKeyboardButton(
                    text=t("vpn.open_subscription"),
                    url=issued.subscription_url,
                ),
            ],
        )
    rows.append(
        [
            InlineKeyboardButton(
                text=t("vpn.download_happ"),
                url=HAPP_DOWNLOAD_URL,
            ),
        ],
    )
    return InlineKeyboardMarkup(inline_keyboard=rows)


def decode_qr(issued: IssuedVpnOut) -> bytes:
    """Decode the base64-encoded QR-code PNG."""
    return base64.b64decode(issued.qr_png_base64)


async def send_issued_vpn(
    message: Message,
    issued: IssuedVpnOut,
    t: Translator,
) -> None:
    """Send the full issued-VPN UX to a chat.

    Two messages are sent in sequence: the header + Happ buttons + VLESS
    fallback, then the QR code as a photo. This mirrors the product spec
    and guarantees the user sees a working link even if buttons fail to
    open (e.g. desktop Telegram without Happ installed).
    """
    body_parts: Sequence[str] = (
        t("vpn.issued_header"),
        t("vpn.vless_fallback", link=issued.vless_link),
    )
    await message.answer(
        "\n\n".join(body_parts),
        reply_markup=happ_buttons(issued, t),
        parse_mode="HTML",
        disable_web_page_preview=True,
    )
    qr_bytes = decode_qr(issued)
    photo = BufferedInputFile(qr_bytes, filename="vpn.png")
    await message.answer_photo(photo=photo, caption=t("vpn.qr_caption"))
