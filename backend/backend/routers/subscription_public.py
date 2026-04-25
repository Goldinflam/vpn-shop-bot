"""Unauthenticated ``GET /sub/{sub_token}`` — VLESS list for VPN clients.

Happ and other VLESS clients fetch this URL periodically to refresh their
config. The response is plain text, one ``vless://`` line per active server.
404 if the token is unknown OR the subscription is not ACTIVE.
"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, status
from fastapi.responses import PlainTextResponse
from shared.contracts.errors import NotFoundError
from shared.contracts.http import SUB_PUBLIC

from backend.deps import SubscriptionServiceDep

router = APIRouter(tags=["public/sub"])


@router.get(SUB_PUBLIC, response_class=PlainTextResponse)
async def get_sub_links(sub_token: str, service: SubscriptionServiceDep) -> PlainTextResponse:
    try:
        clients = await service.list_active_clients_for_token(sub_token)
    except NotFoundError as exc:  # noqa: F841 — re-raised as 404 below
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="subscription_not_found"
        ) from exc
    if not clients:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="subscription_not_active",
        )
    body = "\n".join(c.vless_link for c in clients) + "\n"
    return PlainTextResponse(content=body, media_type="text/plain; charset=utf-8")
