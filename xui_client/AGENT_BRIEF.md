# xui_client Agent — Техническое задание

> Этот файл — источник правды для дочерней Devin-сессии, работающей только в папке `xui_client/`.
> Не редактируй файлы вне `xui_client/`, кроме как через PR в `shared/contracts/xui.py` (если нашёл баг в контракте).

## Область ответственности
Обёртка над [`py3xui`](https://github.com/iwatkot/py3xui) под домен нашего приложения.
Предоставляет backend'у высокоуровневый асинхронный API без необходимости знать детали 3x-ui.

## Не твоя область
- `backend/`, `bot/` — не трогай.
- БД, платежи, Telegram — не твоё.

## Стек
- `py3xui >= 0.5` (async клиент к 3x-ui)
- `qrcode[pil]` — генерация QR-кодов
- `tenacity` — ретраи
- `httpx` — (опционально, для sub-URL и здоровья панели)
- `pytest`, `pytest-httpx` для тестов

## Публичный API
Реализуй класс `XUIClient`, экспортируй через `xui_client/__init__.py`:

```python
from xui_client import XUIClient

client = XUIClient(
    host="https://panel.example.com",
    username="admin",
    password="admin",
    tls_verify=True,
    default_inbound_id=1,
)
await client.start()   # login
# ... use ...
await client.close()
```

Класс ДОЛЖЕН удовлетворять `shared.contracts.xui.XUIClientProtocol`.
Все методы из `XUIClientProtocol` — обязательны. Добавление новых методов — только через PR в `shared/contracts/xui.py`.

## Требования
1. **Auto re-login**: при 401 от панели — прозрачно перелогиниться и повторить запрос (tenacity, 1 ретрай).
2. **Таймауты**: дефолт 10 секунд на запрос, настраивается в конструкторе.
3. **VLESS-ссылка**: собирай полный `vless://{uuid}@{host}:{port}?...#{remark}` по настройкам inbound (pbk/sid/sni/fp/security из streamSettings). Поддержи как минимум VLESS + Reality и VLESS + TLS.
4. **QR**: `qrcode.make(vless_link)` → PNG bytes.
5. **Subscription URL**: если в панели включен `subJson`/`subPath`, верни соответствующий `https://host:subPort/{subPath}/{subId}`. Если не настроено — `None`.
6. **Идемпотентность create**: если клиент с данным `email` уже существует в inbound — НЕ бросай ошибку, а верни существующего (лог: warning).
7. **Нормализация email**: `tg_{telegram_id}_{random6}`, если `telegram_id` передан; иначе принимай как есть.
8. **Ошибки**: бросай только `shared.contracts.errors.XUIError` и его подклассы. Оборачивай любые исключения из `py3xui`.

## Структура модуля
```
xui_client/
├── xui_client/
│   ├── __init__.py          # re-export XUIClient
│   ├── client.py            # XUIClient — основной класс
│   ├── vless.py             # сборка vless:// URL
│   ├── qr.py                # генерация PNG
│   └── retries.py           # tenacity-конфиг
├── tests/
│   ├── conftest.py          # фикстура с pytest-httpx mock panel
│   ├── test_client.py
│   ├── test_vless.py
│   └── test_qr.py
└── pyproject.toml
```

## Тесты
- Моки сетевых вызовов через `pytest-httpx`. **Не** требуй живую 3x-ui панель.
- Минимум: create (включая идемпотентность), disable, enable, delete, extend, get_traffic, reset_traffic, list_inbounds, health_check, auto re-login.
- Строй сценарии: успех, 401→релогин→повтор, 404→`XUIClientNotFound`, 500→ретрай.
- `test_vless.py`: парсь inbound fixture (Reality + TLS), проверь что собранный URL валиден и содержит pbk/sid/sni/fp.

## Качество
- `ruff check xui_client/` и `mypy xui_client/ --strict` — чисто.
- Docstring у каждого публичного метода.

## Готовность
1. `XUIClient` полностью реализует `XUIClientProtocol`.
2. `pytest xui_client/ -v` зелёный (все сетевые вызовы замоканы).
3. В README модуля пример использования из 15 строк.
4. PR в ветку `agent/xui-client` на базе `main`, заголовок `[xui_client] initial implementation`.
