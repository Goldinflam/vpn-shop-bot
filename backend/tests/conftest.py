"""Shared pytest fixtures."""

from __future__ import annotations

from collections.abc import AsyncIterator
from decimal import Decimal
from typing import cast
from unittest.mock import AsyncMock

import pytest
import pytest_asyncio
from backend.config import get_settings
from backend.db import Base
from backend.main import create_app
from backend.models import Plan, Server, User
from backend.xui_pool import XUIPool
from httpx import ASGITransport, AsyncClient
from shared.contracts.http import HEADER_ADMIN_TOKEN, HEADER_BOT_TOKEN
from shared.contracts.xui import VlessClientResult, XUIClientProtocol
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from backend import db as db_module
from backend import xui_pool as xui_pool_module


class FakeXUIPool(XUIPool):
    """Test pool that returns the same mock client for every server."""

    def __init__(self, client: XUIClientProtocol) -> None:
        super().__init__(builder=lambda _server: client)
        self._fixed_client = client

    async def get(self, server: Server) -> XUIClientProtocol:
        return self._fixed_client


@pytest_asyncio.fixture
async def engine() -> AsyncIterator[AsyncEngine]:
    eng = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        future=True,
        connect_args={"check_same_thread": False},
    )
    async with eng.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield eng
    await eng.dispose()


@pytest_asyncio.fixture
async def sessionmaker(engine: AsyncEngine) -> async_sessionmaker[AsyncSession]:
    return async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)


@pytest_asyncio.fixture
async def session(
    sessionmaker: async_sessionmaker[AsyncSession],
) -> AsyncIterator[AsyncSession]:
    async with sessionmaker() as s:
        yield s


@pytest.fixture
def xui_mock() -> XUIClientProtocol:
    mock = AsyncMock(spec=XUIClientProtocol)
    mock.create_vless_client.return_value = VlessClientResult(
        client_uuid="uuid-test-1",
        email="tg1-0",
        inbound_id=1,
        vless_link="vless://uuid-test-1@example.com:443?type=tcp#plan",
        subscription_url=None,
        qr_png=b"\x89PNG\r\n\x1a\n",
    )
    mock.health_check.return_value = True
    return cast(XUIClientProtocol, mock)


@pytest.fixture
def xui_pool(xui_mock: XUIClientProtocol) -> FakeXUIPool:
    return FakeXUIPool(xui_mock)


@pytest_asyncio.fixture
async def server_row(session: AsyncSession) -> Server:
    """Insert a default enabled server so multi-server provisioning works."""
    server = Server(
        name="test",
        country_code="XX",
        host="https://panel.test",
        username="admin",
        password="admin",
        inbound_id=1,
        tls_verify=False,
        enabled=True,
    )
    session.add(server)
    await session.commit()
    await session.refresh(server)
    return server


@pytest_asyncio.fixture
async def client(
    sessionmaker: async_sessionmaker[AsyncSession],
    xui_pool: FakeXUIPool,
    server_row: Server,  # ensure at least one enabled server exists
) -> AsyncIterator[AsyncClient]:
    # Tell the main app it is in test mode (scheduler disabled).
    import os

    os.environ["ENVIRONMENT"] = "test"
    get_settings.cache_clear()

    db_module.set_sessionmaker(sessionmaker)
    xui_pool_module.set_xui_pool(xui_pool)

    app = create_app()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


@pytest.fixture
def bot_headers() -> dict[str, str]:
    cfg = get_settings()
    return {HEADER_BOT_TOKEN: cfg.bot_api_token}


@pytest.fixture
def admin_headers(bot_headers: dict[str, str]) -> dict[str, str]:
    cfg = get_settings()
    return {**bot_headers, HEADER_ADMIN_TOKEN: cfg.admin_api_token}


@pytest_asyncio.fixture
async def user_row(session: AsyncSession) -> User:
    user = User(telegram_id=1001, username="alice", first_name="Alice")
    session.add(user)
    await session.commit()
    await session.refresh(user)
    return user


@pytest_asyncio.fixture
async def plan_row(session: AsyncSession) -> Plan:
    plan = Plan(
        name="1 month",
        description="Test plan",
        duration_days=30,
        traffic_gb=50,
        price=Decimal("299.00"),
    )
    session.add(plan)
    await session.commit()
    await session.refresh(plan)
    return plan
