"""Global exception handlers translating domain errors to HTTP responses."""

from __future__ import annotations

from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse
from shared.contracts.errors import (
    AlreadyExistsError,
    NotFoundError,
    PaymentError,
    PaymentProviderError,
    PromoAlreadyUsedError,
    PromoError,
    PromoExhaustedError,
    PromoExpiredError,
    PromoNotFoundError,
    SubscriptionError,
    TrialAlreadyClaimedError,
    VPNShopError,
    XUIError,
)


def _json(status_code: int, code: str, message: str) -> JSONResponse:
    return JSONResponse(status_code=status_code, content={"code": code, "detail": message})


async def _not_found(_request: Request, exc: Exception) -> JSONResponse:
    return _json(status.HTTP_404_NOT_FOUND, "not_found", str(exc))


async def _already_exists(_request: Request, exc: Exception) -> JSONResponse:
    return _json(status.HTTP_409_CONFLICT, "already_exists", str(exc))


async def _payment_provider(_request: Request, exc: Exception) -> JSONResponse:
    return _json(status.HTTP_502_BAD_GATEWAY, "payment_provider_error", str(exc))


async def _payment(_request: Request, exc: Exception) -> JSONResponse:
    return _json(status.HTTP_400_BAD_REQUEST, "payment_error", str(exc))


async def _subscription(_request: Request, exc: Exception) -> JSONResponse:
    return _json(status.HTTP_400_BAD_REQUEST, "subscription_error", str(exc))


async def _xui(_request: Request, exc: Exception) -> JSONResponse:
    return _json(status.HTTP_502_BAD_GATEWAY, "xui_error", str(exc))


async def _promo_not_found(_request: Request, exc: Exception) -> JSONResponse:
    return _json(status.HTTP_404_NOT_FOUND, "promo_not_found", str(exc))


async def _promo_expired(_request: Request, exc: Exception) -> JSONResponse:
    return _json(status.HTTP_410_GONE, "promo_expired", str(exc))


async def _promo_exhausted(_request: Request, exc: Exception) -> JSONResponse:
    return _json(status.HTTP_409_CONFLICT, "promo_exhausted", str(exc))


async def _promo_already_used(_request: Request, exc: Exception) -> JSONResponse:
    return _json(status.HTTP_409_CONFLICT, "promo_already_used", str(exc))


async def _promo(_request: Request, exc: Exception) -> JSONResponse:
    return _json(status.HTTP_400_BAD_REQUEST, "promo_error", str(exc))


async def _trial_claimed(_request: Request, exc: Exception) -> JSONResponse:
    return _json(status.HTTP_409_CONFLICT, "trial_already_claimed", str(exc))


async def _domain(_request: Request, exc: Exception) -> JSONResponse:
    return _json(status.HTTP_400_BAD_REQUEST, "domain_error", str(exc))


def register_exception_handlers(app: FastAPI) -> None:
    """Attach domain exception handlers to ``app``."""
    app.add_exception_handler(NotFoundError, _not_found)
    app.add_exception_handler(AlreadyExistsError, _already_exists)
    app.add_exception_handler(PaymentProviderError, _payment_provider)
    app.add_exception_handler(PaymentError, _payment)
    app.add_exception_handler(SubscriptionError, _subscription)
    app.add_exception_handler(XUIError, _xui)
    app.add_exception_handler(PromoNotFoundError, _promo_not_found)
    app.add_exception_handler(PromoExpiredError, _promo_expired)
    app.add_exception_handler(PromoExhaustedError, _promo_exhausted)
    app.add_exception_handler(PromoAlreadyUsedError, _promo_already_used)
    app.add_exception_handler(TrialAlreadyClaimedError, _trial_claimed)
    app.add_exception_handler(PromoError, _promo)
    app.add_exception_handler(VPNShopError, _domain)
