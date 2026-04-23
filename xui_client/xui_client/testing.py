"""Test helpers for users of :mod:`xui_client`.

Exposes a small fixture DSL around ``pytest-httpx`` so downstream consumers
(and our own tests) can mock a 3x-ui panel at the HTTP level. The module
is intentionally lightweight — it only provides type aliases and a
:class:`MockPanel` class; actual fixtures live in the consumer's
``conftest.py``.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from pytest_httpx import HTTPXMock

InboundDict = dict[str, Any]
ClientDict = dict[str, Any]
StreamDict = dict[str, Any]

InboundFactory = Callable[..., InboundDict]
ClientFactory = Callable[..., ClientDict]


@dataclass
class MockPanel:
    """Bundle a ``pytest-httpx`` mock with panel-aware helpers.

    Each ``mock_*`` method registers a canned response for a single
    3x-ui endpoint so the ``XUIClient`` can be exercised end-to-end
    without a live panel.
    """

    base: str
    httpx_mock: HTTPXMock

    def url(self, path: str) -> str:
        return f"{self.base}/{path.lstrip('/')}"

    def envelope(
        self, obj: Any = None, *, success: bool = True, msg: str = ""
    ) -> dict[str, Any]:
        return {"success": success, "msg": msg, "obj": obj}

    def mock_login(self, *, is_reusable: bool = True) -> None:
        self.httpx_mock.add_response(
            method="POST",
            url=self.url("/login"),
            json=self.envelope(True),
            headers={"set-cookie": "3x-ui=session-abc; Path=/; HttpOnly"},
            is_reusable=is_reusable,
        )

    def mock_get_inbound(
        self, inbound: InboundDict, *, inbound_id: int | None = None
    ) -> None:
        iid = inbound_id if inbound_id is not None else int(inbound["id"])
        self.httpx_mock.add_response(
            method="GET",
            url=self.url(f"/panel/api/inbounds/get/{iid}"),
            json=self.envelope(inbound),
        )

    def mock_list_inbounds(self, inbounds: list[InboundDict]) -> None:
        self.httpx_mock.add_response(
            method="GET",
            url=self.url("/panel/api/inbounds/list"),
            json=self.envelope(inbounds),
        )

    def mock_add_client(self) -> None:
        self.httpx_mock.add_response(
            method="POST",
            url=self.url("/panel/api/inbounds/addClient"),
            json=self.envelope(None),
        )

    def mock_update_client(self, client_uuid: str) -> None:
        self.httpx_mock.add_response(
            method="POST",
            url=self.url(f"/panel/api/inbounds/updateClient/{client_uuid}"),
            json=self.envelope(None),
        )

    def mock_delete_client(self, *, inbound_id: int, client_uuid: str) -> None:
        self.httpx_mock.add_response(
            method="POST",
            url=self.url(
                f"/panel/api/inbounds/{inbound_id}/delClient/{client_uuid}"
            ),
            json=self.envelope(None),
        )

    def mock_get_traffic_by_email(
        self, email: str, client: ClientDict | None
    ) -> None:
        self.httpx_mock.add_response(
            method="GET",
            url=self.url(f"/panel/api/inbounds/getClientTraffics/{email}"),
            json=self.envelope(client),
        )

    def mock_reset_stats(self, *, inbound_id: int, email: str) -> None:
        self.httpx_mock.add_response(
            method="POST",
            url=self.url(
                f"/panel/api/inbounds/{inbound_id}/resetClientTraffic/{email}"
            ),
            json=self.envelope(None),
        )

    def mock_status_code(self, *, method: str, path: str, status: int) -> None:
        self.httpx_mock.add_response(
            method=method,
            url=self.url(path),
            status_code=status,
            json={"success": False, "msg": f"HTTP {status}"},
        )
