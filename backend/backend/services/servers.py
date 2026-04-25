"""CRUD for the ``Server`` (x-ui panel) admin API."""

from __future__ import annotations

from shared.contracts.errors import NotFoundError
from shared.schemas import ServerIn, ServerUpdate
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.models import Server


class ServerService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def list_all(self) -> list[Server]:
        result = await self._session.execute(select(Server).order_by(Server.id))
        return list(result.scalars().all())

    async def get(self, server_id: int) -> Server:
        server = await self._session.get(Server, server_id)
        if server is None:
            raise NotFoundError(f"Server {server_id} not found")
        return server

    async def create(self, dto: ServerIn) -> Server:
        server = Server(
            name=dto.name,
            country_code=dto.country_code.upper(),
            host=dto.host.rstrip("/"),
            username=dto.username,
            password=dto.password,
            inbound_id=dto.inbound_id,
            public_host=dto.public_host,
            subscription_base_url=dto.subscription_base_url,
            tls_verify=dto.tls_verify,
            enabled=dto.enabled,
        )
        self._session.add(server)
        await self._session.flush()
        await self._session.refresh(server)
        return server

    async def update(self, server_id: int, dto: ServerUpdate) -> Server:
        server = await self.get(server_id)
        data = dto.model_dump(exclude_unset=True)
        if "country_code" in data and data["country_code"] is not None:
            data["country_code"] = data["country_code"].upper()
        if "host" in data and data["host"] is not None:
            data["host"] = data["host"].rstrip("/")
        for k, v in data.items():
            setattr(server, k, v)
        await self._session.flush()
        await self._session.refresh(server)
        return server

    async def delete(self, server_id: int) -> None:
        server = await self.get(server_id)
        await self._session.delete(server)
        await self._session.flush()
