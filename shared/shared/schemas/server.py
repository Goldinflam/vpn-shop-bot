"""DTOs for the ``Server`` (x-ui panel host) admin API."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class ServerIn(BaseModel):
    """Input DTO for creating an x-ui panel server."""

    model_config = ConfigDict(extra="forbid")

    name: str = Field(min_length=1, max_length=128)
    country_code: str = Field(min_length=2, max_length=8, description="ISO 3166-1 alpha-2/3")
    host: str = Field(min_length=1, description="x-ui panel base URL, e.g. https://1.2.3.4:54321")
    username: str
    password: str
    inbound_id: int = Field(ge=1)
    public_host: str | None = Field(
        default=None,
        description="Hostname embedded into VLESS URLs; defaults to host's hostname.",
    )
    subscription_base_url: str | None = Field(
        default=None,
        description="If the panel exposes a /sub endpoint, its base URL.",
    )
    tls_verify: bool = True
    enabled: bool = True


class ServerUpdate(BaseModel):
    """Partial update; all fields optional."""

    model_config = ConfigDict(extra="forbid")

    name: str | None = Field(default=None, min_length=1, max_length=128)
    country_code: str | None = Field(default=None, min_length=2, max_length=8)
    host: str | None = None
    username: str | None = None
    password: str | None = None
    inbound_id: int | None = Field(default=None, ge=1)
    public_host: str | None = None
    subscription_base_url: str | None = None
    tls_verify: bool | None = None
    enabled: bool | None = None


class ServerOut(BaseModel):
    """Output DTO. ``password`` is intentionally omitted."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    country_code: str
    host: str
    username: str
    inbound_id: int
    public_host: str | None
    subscription_base_url: str | None
    tls_verify: bool
    enabled: bool
    created_at: datetime
    updated_at: datetime
