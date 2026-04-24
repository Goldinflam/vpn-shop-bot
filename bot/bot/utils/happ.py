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
import html
import logging
from typing import Final

from aiogram.exceptions import TelegramBadRequest
from aiogram.types import (
    BufferedInputFile,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    Message,
)
from shared.schemas import IssuedVpnOut

from bot.i18n import Translator

logger = logging.getLogger(__name__)

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
    fallback, then the QR code as a photo.

    Robustness: if Telegram rejects the Happ deep-link button (custom URL
    scheme on some Telegram Desktop builds), we retry without the button
    and inline the ``happ://`` link as selectable text. Similarly for
    rendering errors on the photo step.
    """
    vless_safe = html.escape(issued.vless_link)
    body = "\n\n".join(
        (
            t("vpn.issued_header"),
            t("vpn.vless_fallback", link=vless_safe),
        )
    )
    try:
        await message.answer(
            body,
            reply_markup=happ_buttons(issued, t),
            parse_mode="HTML",
            disable_web_page_preview=True,
        )
    except TelegramBadRequest as exc:
        logger.warning(
            "Happ inline-button rejected by Telegram, falling back to text: %s", exc
        )
        happ_safe = html.escape(issued.happ_import_url)
        fallback = (
            f"{body}\n\n"
            f"{t('vpn.happ_connect')}: <code>{happ_safe}</code>\n"
            f"{t('vpn.download_happ')}: {HAPP_DOWNLOAD_URL}"
        )
        await message.answer(
            fallback,
            parse_mode="HTML",
            disable_web_page_preview=True,
        )
    try:
        qr_bytes = decode_qr(issued)
        photo = BufferedInputFile(qr_bytes, filename="vpn.png")
        await message.answer_photo(photo=photo, caption=t("vpn.qr_caption"))
    except Exception as exc:  # noqa: BLE001 — QR is optional, VPN already delivered
        logger.warning("QR photo failed to send (VPN delivered): %s", exc)
