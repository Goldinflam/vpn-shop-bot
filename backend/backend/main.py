"""FastAPI application entrypoint."""

from __future__ import annotations

import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from fastapi import FastAPI
from shared.contracts.http import API_PREFIX

from backend.config import get_settings
from backend.errors import register_exception_handlers
from backend.routers import (
    admin_router,
    health_router,
    payments_router,
    plans_router,
    subscriptions_router,
    users_router,
)
from backend.scheduler import build_scheduler


def _configure_logging() -> None:
    cfg = get_settings()
    logging.basicConfig(
        level=getattr(logging, cfg.log_level.upper(), logging.INFO),
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    _configure_logging()
    cfg = get_settings()
    scheduler: AsyncIOScheduler | None = None
    if cfg.environment != "test":
        scheduler = build_scheduler(cfg)
        scheduler.start()
    app.state.scheduler = scheduler
    try:
        yield
    finally:
        if scheduler is not None:
            scheduler.shutdown(wait=False)


def create_app() -> FastAPI:
    app = FastAPI(title="vpn-shop-backend", version="0.1.0", lifespan=lifespan)

    register_exception_handlers(app)

    app.include_router(health_router)
    app.include_router(users_router, prefix=API_PREFIX)
    app.include_router(plans_router, prefix=API_PREFIX)
    app.include_router(subscriptions_router, prefix=API_PREFIX)
    app.include_router(payments_router, prefix=API_PREFIX)
    app.include_router(admin_router, prefix=API_PREFIX)

    return app


app = create_app()
