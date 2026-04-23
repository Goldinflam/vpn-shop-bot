"""Tests for :class:`bot.api_client.BackendClient` with pytest-httpx."""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Any

import pytest
from bot.api_client import (
    AuthError,
    BackendClient,
    BackendError,
    BackendUnavailableError,
    NotFoundError,
    ValidationError,
)
from pytest_httpx import HTTPXMock
from shared.contracts import http as http_contract
from shared.enums import (
    Currency,
    Locale,
    PaymentProvider,
    PaymentStatus,
    SubscriptionStatus,
)
from shared.schemas import (
    PaymentCreate,
    SubscriptionRenew,
    UserUpsert,
)

BASE_URL = "http://backend.test:8000"
BOT_TOKEN = "bot-token-xyz"  # noqa: S105
ADMIN_TOKEN = "admin-token-xyz"  # noqa: S105


def _url(path: str) -> str:
    return f"{BASE_URL}{http_contract.API_PREFIX}{path}"


@pytest.fixture
async def client() -> BackendClient:
    return BackendClient(
        base_url=BASE_URL,
        bot_token=BOT_TOKEN,
        admin_token=ADMIN_TOKEN,
    )


def _user_payload(**overrides: Any) -> dict[str, Any]:
    payload = {
        "id": 1,
        "telegram_id": 111,
        "username": "u",
        "first_name": "F",
        "last_name": "L",
        "locale": Locale.RU.value,
        "balance": "0",
        "is_admin": False,
        "is_banned": False,
        "created_at": datetime(2024, 1, 1, 0, 0, 0).isoformat(),
    }
    payload.update(overrides)
    return payload


def _plan_payload(plan_id: int = 1) -> dict[str, Any]:
    return {
        "id": plan_id,
        "name": "30d",
        "description": None,
        "duration_days": 30,
        "traffic_gb": 100,
        "price": "499.00",
        "currency": Currency.RUB.value,
        "is_active": True,
        "sort_order": 0,
    }


def _payment_payload(**overrides: Any) -> dict[str, Any]:
    payload = {
        "id": 7,
        "user_id": 1,
        "plan_id": 1,
        "subscription_id": None,
        "amount": "499.00",
        "currency": Currency.RUB.value,
        "provider": PaymentProvider.YOOKASSA.value,
        "provider_payment_id": None,
        "payment_url": "https://pay.example/7",
        "status": PaymentStatus.PENDING.value,
        "created_at": datetime(2024, 1, 1, 0, 0, 0).isoformat(),
    }
    payload.update(overrides)
    return payload


def _subscription_payload(sub_id: int = 42) -> dict[str, Any]:
    return {
        "id": sub_id,
        "user_id": 1,
        "plan_id": 1,
        "xui_client_uuid": "uuid-1",
        "xui_inbound_id": 1,
        "xui_email": "u@vpn",
        "vless_link": "vless://abc",
        "traffic_limit_bytes": 0,
        "traffic_used_bytes": 0,
        "starts_at": datetime(2024, 1, 1).isoformat(),
        "expires_at": datetime(2024, 2, 1).isoformat(),
        "status": SubscriptionStatus.ACTIVE.value,
        "created_at": datetime(2024, 1, 1).isoformat(),
    }


async def test_upsert_user_sends_bot_token_header(
    client: BackendClient,
    httpx_mock: HTTPXMock,
) -> None:
    httpx_mock.add_response(
        method="POST",
        url=_url(http_contract.USERS_UPSERT),
        json=_user_payload(),
    )
    result = await client.upsert_user(UserUpsert(telegram_id=111, username="u"))
    assert result.telegram_id == 111

    request = httpx_mock.get_request()
    assert request is not None
    assert request.headers[http_contract.HEADER_BOT_TOKEN] == BOT_TOKEN
    assert http_contract.HEADER_ADMIN_TOKEN not in request.headers
    await client.aclose()


async def test_get_user(client: BackendClient, httpx_mock: HTTPXMock) -> None:
    httpx_mock.add_response(
        method="GET",
        url=_url(http_contract.USER_GET.format(telegram_id=111)),
        json=_user_payload(),
    )
    user = await client.get_user(111)
    assert user.telegram_id == 111
    await client.aclose()


async def test_user_subscriptions(client: BackendClient, httpx_mock: HTTPXMock) -> None:
    httpx_mock.add_response(
        method="GET",
        url=_url(http_contract.USER_SUBSCRIPTIONS.format(telegram_id=111)),
        json=[_subscription_payload()],
    )
    subs = await client.user_subscriptions(111)
    assert len(subs) == 1
    assert subs[0].vless_link == "vless://abc"
    await client.aclose()


async def test_list_plans_returns_plans(
    client: BackendClient,
    httpx_mock: HTTPXMock,
) -> None:
    httpx_mock.add_response(
        method="GET",
        url=_url(http_contract.PLANS_LIST),
        json=[_plan_payload(1), _plan_payload(2)],
    )
    plans = await client.list_plans()
    assert [plan.id for plan in plans] == [1, 2]
    assert plans[0].price == Decimal("499.00")
    await client.aclose()


async def test_get_plan(client: BackendClient, httpx_mock: HTTPXMock) -> None:
    httpx_mock.add_response(
        method="GET",
        url=_url(http_contract.PLAN_GET.format(plan_id=1)),
        json=_plan_payload(1),
    )
    plan = await client.get_plan(1)
    assert plan.name == "30d"
    await client.aclose()


async def test_create_payment_round_trips_body(
    client: BackendClient,
    httpx_mock: HTTPXMock,
) -> None:
    httpx_mock.add_response(
        method="POST",
        url=_url(http_contract.PAYMENTS_CREATE),
        json=_payment_payload(),
    )
    payment = await client.create_payment(
        PaymentCreate(telegram_id=111, plan_id=1, provider=PaymentProvider.YOOKASSA),
    )
    assert payment.id == 7
    assert payment.status is PaymentStatus.PENDING

    request = httpx_mock.get_request()
    assert request is not None
    body = request.read().decode()
    assert '"telegram_id":111' in body
    assert '"plan_id":1' in body
    assert '"provider":"yookassa"' in body
    await client.aclose()


async def test_get_payment(client: BackendClient, httpx_mock: HTTPXMock) -> None:
    httpx_mock.add_response(
        method="GET",
        url=_url(http_contract.PAYMENT_GET.format(payment_id=7)),
        json=_payment_payload(status=PaymentStatus.SUCCEEDED.value),
    )
    payment = await client.get_payment(7)
    assert payment.status is PaymentStatus.SUCCEEDED
    await client.aclose()


async def test_get_subscription(client: BackendClient, httpx_mock: HTTPXMock) -> None:
    httpx_mock.add_response(
        method="GET",
        url=_url(http_contract.SUBSCRIPTION_GET.format(subscription_id=42)),
        json=_subscription_payload(42),
    )
    sub = await client.get_subscription(42)
    assert sub.id == 42
    await client.aclose()


async def test_renew_subscription(client: BackendClient, httpx_mock: HTTPXMock) -> None:
    httpx_mock.add_response(
        method="POST",
        url=_url(http_contract.SUBSCRIPTION_RENEW.format(subscription_id=42)),
        json=_payment_payload(id=8, subscription_id=42),
    )
    payment = await client.renew_subscription(42, SubscriptionRenew(plan_id=1))
    assert payment.id == 8
    assert payment.subscription_id == 42
    await client.aclose()


async def test_subscription_qr_returns_png_bytes(
    client: BackendClient,
    httpx_mock: HTTPXMock,
) -> None:
    httpx_mock.add_response(
        method="GET",
        url=_url(http_contract.SUBSCRIPTION_QR.format(subscription_id=42)),
        content=b"\x89PNG\r\n\x1a\n",
        headers={"content-type": "image/png"},
    )
    data = await client.subscription_qr(42)
    assert data.startswith(b"\x89PNG")
    await client.aclose()


async def test_admin_stats_sends_admin_token(
    client: BackendClient,
    httpx_mock: HTTPXMock,
) -> None:
    httpx_mock.add_response(
        method="GET",
        url=_url(http_contract.ADMIN_STATS),
        json={"users": 10, "subs": 5},
    )
    stats = await client.admin_stats()
    assert stats == {"users": 10, "subs": 5}

    request = httpx_mock.get_request()
    assert request is not None
    assert request.headers[http_contract.HEADER_BOT_TOKEN] == BOT_TOKEN
    assert request.headers[http_contract.HEADER_ADMIN_TOKEN] == ADMIN_TOKEN
    await client.aclose()


async def test_admin_broadcast(client: BackendClient, httpx_mock: HTTPXMock) -> None:
    httpx_mock.add_response(
        method="POST",
        url=_url(http_contract.ADMIN_BROADCAST),
        json={"recipients": 3},
    )
    result = await client.admin_broadcast("hello")
    assert result == {"recipients": 3}
    await client.aclose()


async def test_admin_call_without_admin_token_raises() -> None:
    client = BackendClient(base_url=BASE_URL, bot_token=BOT_TOKEN, admin_token=None)
    with pytest.raises(AuthError):
        await client.admin_stats()
    await client.aclose()


async def test_404_translates_to_not_found(
    client: BackendClient,
    httpx_mock: HTTPXMock,
) -> None:
    httpx_mock.add_response(
        method="GET",
        url=_url(http_contract.USER_GET.format(telegram_id=999)),
        status_code=404,
        json={"detail": "user missing"},
    )
    with pytest.raises(NotFoundError) as exc:
        await client.get_user(999)
    assert exc.value.status_code == 404
    await client.aclose()


async def test_401_translates_to_auth_error(
    client: BackendClient,
    httpx_mock: HTTPXMock,
) -> None:
    httpx_mock.add_response(
        method="GET",
        url=_url(http_contract.PLANS_LIST),
        status_code=401,
        json={"detail": "bad token"},
    )
    with pytest.raises(AuthError):
        await client.list_plans()
    await client.aclose()


async def test_422_translates_to_validation(
    client: BackendClient,
    httpx_mock: HTTPXMock,
) -> None:
    httpx_mock.add_response(
        method="POST",
        url=_url(http_contract.PAYMENTS_CREATE),
        status_code=422,
        json={"detail": "bad body"},
    )
    with pytest.raises(ValidationError):
        await client.create_payment(
            PaymentCreate(telegram_id=111, plan_id=1, provider=PaymentProvider.YOOKASSA),
        )
    await client.aclose()


async def test_500_translates_to_backend_error(
    client: BackendClient,
    httpx_mock: HTTPXMock,
) -> None:
    httpx_mock.add_response(
        method="GET",
        url=_url(http_contract.PLANS_LIST),
        status_code=500,
        text="boom",
    )
    with pytest.raises(BackendError) as exc:
        await client.list_plans()
    assert exc.value.status_code == 500
    await client.aclose()


async def test_network_error_raises_unavailable(
    client: BackendClient,
    httpx_mock: HTTPXMock,
) -> None:
    import httpx

    httpx_mock.add_exception(httpx.ConnectError("boom"))
    with pytest.raises(BackendUnavailableError):
        await client.list_plans()
    await client.aclose()
