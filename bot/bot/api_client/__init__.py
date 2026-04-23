"""Async HTTP client for the backend API.

The bot never touches the database directly — all state lives behind the
backend HTTP API. URL paths and header names come from
:mod:`shared.contracts.http`, which is the single source of truth for the
bot <-> backend contract.
"""

from __future__ import annotations

from types import TracebackType
from typing import Any, Self

import httpx
from shared.contracts import http as http_contract
from shared.schemas import (
    PaymentCreate,
    PaymentOut,
    PlanOut,
    SubscriptionOut,
    SubscriptionRenew,
    UserOut,
    UserUpsert,
)

from bot.api_client.errors import (
    AuthError,
    BackendError,
    BackendUnavailableError,
    NotFoundError,
    ValidationError,
)

__all__ = [
    "AuthError",
    "BackendClient",
    "BackendError",
    "BackendUnavailableError",
    "NotFoundError",
    "ValidationError",
]


class BackendClient:
    """Typed async wrapper around the backend HTTP API.

    Every outgoing request carries ``X-Bot-Token``. Admin endpoints
    additionally send ``X-Admin-Token`` when :attr:`admin_token` is set.
    """

    def __init__(
        self,
        base_url: str,
        bot_token: str,
        admin_token: str | None = None,
        *,
        timeout: float = 10.0,
        client: httpx.AsyncClient | None = None,
    ) -> None:
        self._base_url = base_url.rstrip("/")
        self._prefix = http_contract.API_PREFIX
        self._bot_token = bot_token
        self._admin_token = admin_token
        self._owns_client = client is None
        self._client = client or httpx.AsyncClient(
            base_url=self._base_url,
            timeout=timeout,
        )

    # ---- lifecycle -------------------------------------------------

    async def aclose(self) -> None:
        if self._owns_client:
            await self._client.aclose()

    async def __aenter__(self) -> Self:
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: TracebackType | None,
    ) -> None:
        await self.aclose()

    # ---- internals -------------------------------------------------

    def _url(self, path: str) -> str:
        return f"{self._prefix}{path}"

    def _headers(self, *, admin: bool = False) -> dict[str, str]:
        headers = {http_contract.HEADER_BOT_TOKEN: self._bot_token}
        if admin:
            if not self._admin_token:
                raise AuthError(
                    status_code=0,
                    message="admin endpoint requested but no admin token configured",
                )
            headers[http_contract.HEADER_ADMIN_TOKEN] = self._admin_token
        return headers

    @staticmethod
    def _raise_for_status(response: httpx.Response) -> None:
        if response.is_success:
            return
        try:
            detail = response.json()
        except ValueError:
            message = response.text or response.reason_phrase
        else:
            if isinstance(detail, dict):
                message = str(detail.get("detail", response.text))
            else:
                message = str(detail)
        status = response.status_code
        if status == 404:
            raise NotFoundError(status, message)
        if status in (401, 403):
            raise AuthError(status, message)
        if status == 422:
            raise ValidationError(status, message)
        raise BackendError(status, message)

    async def _request(
        self,
        method: str,
        path: str,
        *,
        admin: bool = False,
        json: Any | None = None,
    ) -> httpx.Response:
        try:
            response = await self._client.request(
                method,
                self._url(path),
                headers=self._headers(admin=admin),
                json=json,
            )
        except httpx.HTTPError as exc:
            raise BackendUnavailableError(str(exc)) from exc
        self._raise_for_status(response)
        return response

    # ---- user ------------------------------------------------------

    async def upsert_user(self, dto: UserUpsert) -> UserOut:
        response = await self._request(
            "POST",
            http_contract.USERS_UPSERT,
            json=dto.model_dump(mode="json"),
        )
        return UserOut.model_validate(response.json())

    async def get_user(self, telegram_id: int) -> UserOut:
        response = await self._request(
            "GET",
            http_contract.USER_GET.format(telegram_id=telegram_id),
        )
        return UserOut.model_validate(response.json())

    async def user_subscriptions(self, telegram_id: int) -> list[SubscriptionOut]:
        response = await self._request(
            "GET",
            http_contract.USER_SUBSCRIPTIONS.format(telegram_id=telegram_id),
        )
        payload = response.json()
        return [SubscriptionOut.model_validate(item) for item in payload]

    # ---- plans -----------------------------------------------------

    async def list_plans(self) -> list[PlanOut]:
        response = await self._request("GET", http_contract.PLANS_LIST)
        payload = response.json()
        return [PlanOut.model_validate(item) for item in payload]

    async def get_plan(self, plan_id: int) -> PlanOut:
        response = await self._request(
            "GET",
            http_contract.PLAN_GET.format(plan_id=plan_id),
        )
        return PlanOut.model_validate(response.json())

    # ---- payments --------------------------------------------------

    async def create_payment(self, dto: PaymentCreate) -> PaymentOut:
        response = await self._request(
            "POST",
            http_contract.PAYMENTS_CREATE,
            json=dto.model_dump(mode="json"),
        )
        return PaymentOut.model_validate(response.json())

    async def get_payment(self, payment_id: int) -> PaymentOut:
        response = await self._request(
            "GET",
            http_contract.PAYMENT_GET.format(payment_id=payment_id),
        )
        return PaymentOut.model_validate(response.json())

    # ---- subscriptions --------------------------------------------

    async def get_subscription(self, subscription_id: int) -> SubscriptionOut:
        response = await self._request(
            "GET",
            http_contract.SUBSCRIPTION_GET.format(subscription_id=subscription_id),
        )
        return SubscriptionOut.model_validate(response.json())

    async def renew_subscription(
        self,
        subscription_id: int,
        dto: SubscriptionRenew,
    ) -> PaymentOut:
        response = await self._request(
            "POST",
            http_contract.SUBSCRIPTION_RENEW.format(subscription_id=subscription_id),
            json=dto.model_dump(mode="json"),
        )
        return PaymentOut.model_validate(response.json())

    async def subscription_qr(self, subscription_id: int) -> bytes:
        """Return a PNG image with a QR code for the subscription."""
        response = await self._request(
            "GET",
            http_contract.SUBSCRIPTION_QR.format(subscription_id=subscription_id),
        )
        return response.content

    # ---- admin -----------------------------------------------------

    async def admin_stats(self) -> dict[str, Any]:
        response = await self._request("GET", http_contract.ADMIN_STATS, admin=True)
        payload: dict[str, Any] = response.json()
        return payload

    async def admin_broadcast(self, text: str) -> dict[str, Any]:
        response = await self._request(
            "POST",
            http_contract.ADMIN_BROADCAST,
            admin=True,
            json={"text": text},
        )
        payload: dict[str, Any] = response.json()
        return payload
