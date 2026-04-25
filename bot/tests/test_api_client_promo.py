"""API-client tests for trial + promo + issued-VPN endpoints."""

from __future__ import annotations

import base64
from datetime import datetime
from typing import Any

import pytest
from bot.api_client import BackendClient
from pytest_httpx import HTTPXMock
from shared.contracts import http as http_contract
from shared.enums import SubscriptionStatus

BASE_URL = "http://backend.test:8000"
BOT_TOKEN = "bot-token-xyz"  # noqa: S105


def _url(path: str) -> str:
    return f"{BASE_URL}{http_contract.API_PREFIX}{path}"


@pytest.fixture
async def client() -> BackendClient:
    return BackendClient(base_url=BASE_URL, bot_token=BOT_TOKEN)


def _issued_payload() -> dict[str, Any]:
    qr = base64.b64encode(b"\x89PNG\r\n\x1a\n").decode("ascii")
    return {
        "subscription": {
            "id": 1,
            "user_id": 1,
            "plan_id": 1,
            "xui_client_uuid": "u",
            "xui_inbound_id": 1,
            "xui_email": "tg",
            "vless_link": "vless://abc",
            "subscription_url": "https://panel/sub/abc",
            "traffic_limit_bytes": 0,
            "traffic_used_bytes": 0,
            "starts_at": datetime(2024, 1, 1).isoformat(),
            "expires_at": datetime(2024, 2, 1).isoformat(),
            "status": SubscriptionStatus.ACTIVE.value,
            "created_at": datetime(2024, 1, 1).isoformat(),
        },
        "vless_link": "vless://abc",
        "subscription_url": "https://panel/sub/abc",
        "qr_png_base64": qr,
        "happ_import_url": "happ://import-sub?url=https%3A%2F%2Fpanel%2Fsub%2Fabc",
    }


async def test_create_trial(client: BackendClient, httpx_mock: HTTPXMock) -> None:
    httpx_mock.add_response(
        method="POST",
        url=_url(http_contract.TRIAL_CREATE),
        json=_issued_payload(),
    )
    issued = await client.create_trial(777)
    assert issued.happ_import_url.startswith("happ://import-sub")
    await client.aclose()


async def test_apply_promo_trial_returns_issued(
    client: BackendClient, httpx_mock: HTTPXMock
) -> None:
    httpx_mock.add_response(
        method="POST",
        url=_url(http_contract.PROMO_APPLY),
        json={
            "code": "FREE7",
            "is_trial": True,
            "issued": _issued_payload(),
            "discount_percent": None,
            "discount_amount": None,
        },
    )
    result = await client.apply_promo(777, "FREE7")
    assert result.is_trial is True
    assert result.issued is not None
    assert result.issued.happ_import_url.startswith("happ://")
    await client.aclose()


async def test_apply_promo_discount(
    client: BackendClient, httpx_mock: HTTPXMock
) -> None:
    httpx_mock.add_response(
        method="POST",
        url=_url(http_contract.PROMO_APPLY),
        json={
            "code": "SAVE20",
            "is_trial": False,
            "issued": None,
            "discount_percent": 20,
            "discount_amount": None,
        },
    )
    result = await client.apply_promo(777, "SAVE20")
    assert result.is_trial is False
    assert result.discount_percent == 20
    assert result.issued is None
    await client.aclose()


async def test_subscription_issued(
    client: BackendClient, httpx_mock: HTTPXMock
) -> None:
    httpx_mock.add_response(
        method="GET",
        url=_url(http_contract.SUBSCRIPTION_ISSUED.format(subscription_id=42)),
        json=_issued_payload(),
    )
    issued = await client.subscription_issued(42)
    assert issued.subscription.id == 1
    await client.aclose()
