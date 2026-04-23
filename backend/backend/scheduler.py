"""APScheduler wiring for periodic jobs."""

from __future__ import annotations

import logging

from apscheduler.schedulers.asyncio import AsyncIOScheduler

from backend.config import Settings, get_settings
from backend.db import get_sessionmaker
from backend.services.subscriptions import SubscriptionService
from backend.xui import get_xui_client

logger = logging.getLogger(__name__)


async def _expire_overdue_job() -> None:
    maker = get_sessionmaker()
    async with maker() as session:
        service = SubscriptionService(session, get_xui_client())
        try:
            n = await service.expire_overdue()
            if n:
                logger.info("expired %d overdue subscription(s)", n)
            await session.commit()
        except Exception:
            await session.rollback()
            raise


def build_scheduler(settings: Settings | None = None) -> AsyncIOScheduler:
    """Build (but do not start) an ``AsyncIOScheduler`` wired with background jobs."""
    cfg = settings or get_settings()
    scheduler = AsyncIOScheduler()
    scheduler.add_job(
        _expire_overdue_job,
        "interval",
        minutes=cfg.expire_cron_minutes,
        id="expire_overdue_subscriptions",
        replace_existing=True,
    )
    return scheduler
