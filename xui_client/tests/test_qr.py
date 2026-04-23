"""Unit tests for :mod:`xui_client.qr`."""

from __future__ import annotations

from xui_client.qr import qr_png

PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"


def test_qr_png_returns_png_bytes() -> None:
    data = qr_png("vless://abc@example.com:443?type=tcp&security=reality#tag")
    assert isinstance(data, bytes)
    assert data.startswith(PNG_SIGNATURE)
    assert len(data) > 100  # sanity: real PNG, not an empty stub


def test_qr_png_deterministic_for_same_input() -> None:
    assert qr_png("hello") == qr_png("hello")


def test_qr_png_different_for_different_inputs() -> None:
    assert qr_png("hello") != qr_png("world")
