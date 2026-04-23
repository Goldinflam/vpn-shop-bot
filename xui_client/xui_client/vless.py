"""Build ``vless://`` connection URLs from 3x-ui inbound objects.

Supports the two protocols configured by 3x-ui panels in practice:

* **VLESS + Reality** — pulls ``pbk``, ``sni``, ``fp``, ``sid`` (first shortId)
  and optionally ``spx`` (spiderX) from ``streamSettings.realitySettings``.
* **VLESS + TLS** — pulls ``sni``, ``fp``, ``alpn`` and ``allowInsecure`` from
  ``streamSettings.tlsSettings``.

Network-specific parameters for ``tcp``, ``ws``, ``grpc`` and ``http2`` are
extracted on a best-effort basis; unknown networks simply get ``type=<name>``.
"""

from __future__ import annotations

import json
from typing import Any
from urllib.parse import quote, urlencode, urlparse

from py3xui.inbound import Inbound
from py3xui.inbound.stream_settings import StreamSettings


def _as_dict(value: Any) -> dict[str, Any]:
    """Coerce a py3xui field that may be a JSON string or a dict to a dict."""
    if isinstance(value, dict):
        return value
    if isinstance(value, str) and value:
        try:
            parsed = json.loads(value)
        except json.JSONDecodeError:
            return {}
        if isinstance(parsed, dict):
            return parsed
    return {}


def _stream(inbound: Inbound) -> StreamSettings | None:
    """Return the StreamSettings model, parsing it if py3xui stored a string."""
    stream = inbound.stream_settings
    if isinstance(stream, StreamSettings):
        return stream
    if isinstance(stream, str) and stream:
        try:
            data = json.loads(stream)
        except json.JSONDecodeError:
            return None
        return StreamSettings(**data)
    return None


def _reality_params(reality: dict[str, Any]) -> dict[str, str]:
    params: dict[str, str] = {"security": "reality"}

    server_names = reality.get("serverNames") or []
    if isinstance(server_names, list) and server_names:
        params["sni"] = str(server_names[0])
    elif isinstance(reality.get("serverName"), str):
        params["sni"] = reality["serverName"]

    settings = _as_dict(reality.get("settings"))
    pbk = settings.get("publicKey") or reality.get("publicKey")
    if pbk:
        params["pbk"] = str(pbk)

    fp = settings.get("fingerprint") or reality.get("fingerprint")
    if fp:
        params["fp"] = str(fp)

    short_ids = reality.get("shortIds") or []
    if isinstance(short_ids, list) and short_ids:
        params["sid"] = str(short_ids[0])

    spx = settings.get("spiderX") or reality.get("spiderX")
    if spx:
        params["spx"] = str(spx)

    return params


def _tls_params(tls: dict[str, Any], fallback_sni: str) -> dict[str, str]:
    params: dict[str, str] = {"security": "tls"}

    sni = tls.get("serverName") or fallback_sni
    if sni:
        params["sni"] = str(sni)

    settings = _as_dict(tls.get("settings"))
    fp = settings.get("fingerprint") or tls.get("fingerprint")
    if fp:
        params["fp"] = str(fp)

    alpn = tls.get("alpn")
    if isinstance(alpn, list) and alpn:
        params["alpn"] = ",".join(str(a) for a in alpn)

    allow_insecure = settings.get("allowInsecure") or tls.get("allowInsecure")
    if allow_insecure:
        params["allowInsecure"] = "1"

    return params


def _network_params(stream: StreamSettings) -> dict[str, str]:
    network = stream.network or "tcp"
    params: dict[str, str] = {"type": network}

    if network == "tcp":
        tcp = stream.tcp_settings or {}
        header = _as_dict(tcp.get("header"))
        header_type = header.get("type")
        if header_type and header_type != "none":
            params["headerType"] = str(header_type)
        if header_type == "http":
            request = _as_dict(header.get("request"))
            path = request.get("path")
            if isinstance(path, list) and path:
                params["path"] = str(path[0])
            host = _as_dict(request.get("headers")).get("Host")
            if isinstance(host, list) and host:
                params["host"] = str(host[0])
    elif network == "ws":
        ws = _as_dict(getattr(stream, "ws_settings", None) or {})
        path = ws.get("path")
        if path:
            params["path"] = str(path)
        host = _as_dict(ws.get("headers")).get("Host")
        if host:
            params["host"] = str(host)
    elif network == "grpc":
        grpc = _as_dict(getattr(stream, "grpc_settings", None) or {})
        service = grpc.get("serviceName")
        if service:
            params["serviceName"] = str(service)
        if grpc.get("multiMode"):
            params["mode"] = "multi"
    elif network in {"h2", "http"}:
        h2 = _as_dict(getattr(stream, "http_settings", None) or {})
        host = h2.get("host")
        if isinstance(host, list) and host:
            params["host"] = ",".join(str(h) for h in host)
        path = h2.get("path")
        if path:
            params["path"] = str(path)

    return params


def public_host_from_url(host_url: str) -> str:
    """Derive a public hostname for a VLESS URL from an 3x-ui panel URL."""
    parsed = urlparse(host_url)
    return parsed.hostname or host_url


def build_vless_link(
    *,
    inbound: Inbound,
    client_uuid: str,
    public_host: str,
    remark: str,
    client_flow: str | None = None,
) -> str:
    """Assemble a full ``vless://`` URL from an inbound + client UUID.

    Supports Reality and TLS security. Unknown security values fall through
    with just the network parameters.
    """
    stream = _stream(inbound)
    params: dict[str, str] = {}

    if stream is not None:
        params.update(_network_params(stream))
        security = (stream.security or "none").lower()
        if security == "reality":
            params.update(_reality_params(stream.reality_settings or {}))
        elif security == "tls":
            params.update(_tls_params(stream.tls_settings or {}, fallback_sni=public_host))
        elif security and security != "none":
            params["security"] = security
        else:
            params["security"] = "none"
    else:
        params["type"] = "tcp"
        params["security"] = "none"

    if client_flow:
        params["flow"] = client_flow

    query = urlencode(params, safe=",:")
    fragment = quote(remark, safe="")
    return f"vless://{client_uuid}@{public_host}:{inbound.port}?{query}#{fragment}"
