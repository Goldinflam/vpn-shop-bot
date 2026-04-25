"""Tests for ``ServerService`` (admin CRUD)."""

from __future__ import annotations

import pytest
from backend.services.servers import ServerService
from shared.contracts.errors import NotFoundError
from shared.schemas import ServerIn, ServerUpdate
from sqlalchemy.ext.asyncio import AsyncSession


def _server_in(**overrides: object) -> ServerIn:
    base: dict[str, object] = {
        "name": "germany-1",
        "country_code": "de",
        "host": "https://panel.de.example.com:54321/",
        "username": "admin",
        "password": "secret",
        "inbound_id": 2,
        "tls_verify": False,
        "enabled": True,
    }
    base.update(overrides)
    return ServerIn.model_validate(base)


async def test_create_uppercases_country_and_strips_host(
    session: AsyncSession,
) -> None:
    svc = ServerService(session)
    server = await svc.create(_server_in())
    await session.commit()
    assert server.country_code == "DE"
    assert server.host == "https://panel.de.example.com:54321"


async def test_list_orders_by_id(session: AsyncSession) -> None:
    svc = ServerService(session)
    a = await svc.create(_server_in(name="a"))
    b = await svc.create(_server_in(name="b"))
    await session.commit()
    listed = await svc.list_all()
    assert [s.id for s in listed] == [a.id, b.id]


async def test_update_partial(session: AsyncSession) -> None:
    svc = ServerService(session)
    server = await svc.create(_server_in())
    await session.commit()
    updated = await svc.update(server.id, ServerUpdate(enabled=False, country_code="nl"))
    await session.commit()
    assert updated.enabled is False
    assert updated.country_code == "NL"
    # untouched
    assert updated.name == "germany-1"


async def test_get_missing_raises(session: AsyncSession) -> None:
    svc = ServerService(session)
    with pytest.raises(NotFoundError):
        await svc.get(404)


async def test_delete(session: AsyncSession) -> None:
    svc = ServerService(session)
    server = await svc.create(_server_in())
    await session.commit()
    await svc.delete(server.id)
    await session.commit()
    with pytest.raises(NotFoundError):
        await svc.get(server.id)
