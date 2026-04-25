"""API tests for ``/api/v1/admin/servers``."""

from __future__ import annotations

from httpx import AsyncClient
from shared.contracts.http import ADMIN_SERVER, ADMIN_SERVERS, API_PREFIX


async def test_admin_servers_requires_admin_token(
    client: AsyncClient, bot_headers: dict[str, str]
) -> None:
    # bot_headers has no admin token
    resp = await client.get(f"{API_PREFIX}{ADMIN_SERVERS}", headers=bot_headers)
    assert resp.status_code == 401


async def test_admin_servers_full_crud(client: AsyncClient, admin_headers: dict[str, str]) -> None:
    payload = {
        "name": "netherlands-1",
        "country_code": "nl",
        "host": "https://panel.nl.example.com:54321/",
        "username": "admin",
        "password": "s3cret",
        "inbound_id": 2,
        "tls_verify": False,
        "enabled": True,
    }
    resp = await client.post(f"{API_PREFIX}{ADMIN_SERVERS}", json=payload, headers=admin_headers)
    assert resp.status_code == 201, resp.text
    body = resp.json()
    server_id = body["id"]
    assert body["country_code"] == "NL"
    assert body["host"].endswith("54321")  # trailing slash trimmed

    resp_list = await client.get(f"{API_PREFIX}{ADMIN_SERVERS}", headers=admin_headers)
    assert resp_list.status_code == 200
    rows = resp_list.json()
    assert any(r["id"] == server_id for r in rows)

    resp_patch = await client.patch(
        f"{API_PREFIX}{ADMIN_SERVER.format(server_id=server_id)}",
        json={"enabled": False},
        headers=admin_headers,
    )
    assert resp_patch.status_code == 200
    assert resp_patch.json()["enabled"] is False

    resp_get = await client.get(
        f"{API_PREFIX}{ADMIN_SERVER.format(server_id=server_id)}",
        headers=admin_headers,
    )
    assert resp_get.status_code == 200
    assert resp_get.json()["id"] == server_id

    resp_del = await client.delete(
        f"{API_PREFIX}{ADMIN_SERVER.format(server_id=server_id)}",
        headers=admin_headers,
    )
    assert resp_del.status_code == 204

    resp_get2 = await client.get(
        f"{API_PREFIX}{ADMIN_SERVER.format(server_id=server_id)}",
        headers=admin_headers,
    )
    assert resp_get2.status_code == 404


async def test_admin_servers_validation(client: AsyncClient, admin_headers: dict[str, str]) -> None:
    resp = await client.post(
        f"{API_PREFIX}{ADMIN_SERVERS}",
        json={"name": "x"},  # missing required fields
        headers=admin_headers,
    )
    assert resp.status_code == 422
