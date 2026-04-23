# xui_client

Async wrapper over [`py3xui`](https://github.com/iwatkot/py3xui) that implements
[`XUIClientProtocol`](../shared/shared/contracts/xui.py) from `shared.contracts.xui`.

Features:

- All 9 protocol methods: create/disable/enable/delete/extend client, get/reset
  traffic, list inbounds, health check.
- VLESS link generation with **Reality** and **TLS** security, parsed directly
  from the inbound's `streamSettings` (`pbk` / `sid` / `sni` / `fp` / `spx` / `alpn`).
- PNG QR codes via `qrcode[pil]`.
- **Auto re-login** on HTTP 401 — one transparent retry, no error propagated.
- **Idempotent `create_vless_client`** — returns the existing client when the
  email (or `tg_{telegram_id}_*` prefix) is already present in the inbound.
- Raises only `shared.contracts.errors.XUIError` and its subclasses.
- **No network in tests** — every call is mocked via `pytest-httpx`.

## Usage

```python
import asyncio
from xui_client import XUIClient

async def main() -> None:
    async with XUIClient(
        host="https://panel.example.com:2053",
        username="admin",
        password="admin",
        default_inbound_id=1,
        public_host="vpn.example.com",
    ) as xui:
        result = await xui.create_vless_client(
            inbound_id=1,
            email="user@example.com",
            expire_ts_ms=1_735_689_600_000,
            traffic_limit_bytes=100 * 1024**3,
            telegram_id=12345,
        )
        print(result.vless_link)

asyncio.run(main())
```

## Development

```bash
pip install -e "./xui_client[dev]"
ruff check xui_client/
mypy xui_client/ --strict
pytest xui_client/ -v
```
