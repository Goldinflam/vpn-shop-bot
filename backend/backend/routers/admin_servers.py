"""Admin CRUD for x-ui panel servers (``/api/v1/admin/servers``)."""

from __future__ import annotations

from fastapi import APIRouter, Depends, status
from shared.contracts.http import ADMIN_SERVER, ADMIN_SERVERS
from shared.schemas import ServerIn, ServerOut, ServerUpdate

from backend.deps import ServerServiceDep, require_admin_token
from backend.xui_pool import get_xui_pool

router = APIRouter(tags=["admin/servers"], dependencies=[Depends(require_admin_token)])


@router.get(ADMIN_SERVERS, response_model=list[ServerOut])
async def list_servers(service: ServerServiceDep) -> list[ServerOut]:
    return [ServerOut.model_validate(s) for s in await service.list_all()]


@router.post(
    ADMIN_SERVERS,
    response_model=ServerOut,
    status_code=status.HTTP_201_CREATED,
)
async def create_server(dto: ServerIn, service: ServerServiceDep) -> ServerOut:
    server = await service.create(dto)
    return ServerOut.model_validate(server)


@router.get(ADMIN_SERVER, response_model=ServerOut)
async def get_server(server_id: int, service: ServerServiceDep) -> ServerOut:
    return ServerOut.model_validate(await service.get(server_id))


@router.patch(ADMIN_SERVER, response_model=ServerOut)
async def update_server(server_id: int, dto: ServerUpdate, service: ServerServiceDep) -> ServerOut:
    server = await service.update(server_id, dto)
    # Drop cached XUI client so next request picks up new credentials.
    await get_xui_pool().remove(server_id)
    return ServerOut.model_validate(server)


@router.delete(ADMIN_SERVER, status_code=status.HTTP_204_NO_CONTENT)
async def delete_server(server_id: int, service: ServerServiceDep) -> None:
    await service.delete(server_id)
    await get_xui_pool().remove(server_id)
