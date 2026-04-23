"""PNG QR-code generation for VLESS links."""

from __future__ import annotations

import io

import qrcode
from qrcode.image.pil import PilImage


def qr_png(data: str) -> bytes:
    """Render *data* as a PNG QR code and return the raw bytes.

    Uses ``qrcode[pil]`` with the PIL image factory so the result is a
    standard PNG-encoded byte string suitable for Telegram ``InputFile``
    payloads and HTTP responses alike.
    """
    img = qrcode.make(data, image_factory=PilImage)
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()
