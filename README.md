# VPN Shop Bot

Telegram-бот для продажи VPN-подписок с интеграцией 3x-ui.

## Архитектура

Монорепо из трёх независимых модулей + общий пакет контрактов:

```
vpn-shop-bot/
├── shared/        Pydantic-схемы / DTO / enums — контракты между модулями
├── xui_client/    Обёртка над py3xui (VLESS, QR, авто-релогин)
├── backend/       FastAPI: users, plans, subscriptions, payments, scheduler
└── bot/           aiogram 3.x: Telegram UI, FSM, i18n ru/en
```

Потоки данных:

```
Telegram  ←──► bot  ──HTTP──►  backend  ──Python──►  xui_client  ──HTTP──►  3x-ui
                                   │
                              PostgreSQL
```

- `bot` **никогда** не трогает БД и не импортирует `py3xui`/`xui_client` — только HTTP к `backend`.
- `backend` **никогда** не вызывает `py3xui` напрямую — только через `xui_client`.
- Все контракты лежат в `shared/` — любое изменение DTO/эндпоинта начинается с PR в `shared/`.

## Стек

- Python 3.11
- aiogram 3.x (bot)
- FastAPI + Uvicorn (backend)
- SQLAlchemy 2.x (async) + Alembic + PostgreSQL (dev: SQLite)
- APScheduler (expiry cron)
- py3xui (обёрнут в `xui_client`)
- Pydantic v2 + pydantic-settings
- Платежи: YooKassa, CryptoBot, Test (всё через `PaymentProviderAdapter` Protocol)
- Docker + docker-compose
- ruff + mypy strict + pytest

## Быстрый старт (Docker)

```bash
cp .env.example .env
# обязательно поменяйте:
#   BOT_TOKEN                — токен от @BotFather
#   BOT_ADMIN_IDS            — ваши telegram user_id через запятую
#   BOT_API_TOKEN            — любая случайная строка, одинаковая у bot и backend
#   ADMIN_API_TOKEN          — любая случайная строка для админских запросов
#   XUI_HOST/USERNAME/PASSWORD/INBOUND_ID — данные вашей 3x-ui панели
# платежи можно оставить пустыми — будет работать TestAdapter

docker compose up --build
```

Сервисы:
- `postgres` — 5432
- `backend` — http://localhost:8000 (health: http://localhost:8000/health, docs: http://localhost:8000/docs)
- `bot` — polling

Миграции БД накатываются автоматически при старте `backend`.

## Dev-разработка (без Docker)

```bash
python3.11 -m venv .venv && source .venv/bin/activate
make install       # pip install -e ./shared ./xui_client ./backend ./bot

# БД (SQLite для разработки):
# в .env: DATABASE_URL=sqlite+aiosqlite:///./dev.db
make migrate       # alembic upgrade head

# Запуск:
uvicorn backend.main:app --reload    # в одном терминале
python -m bot                        # в другом
```

Полезные команды:

```bash
make lint          # ruff check + mypy strict по всем модулям
make test          # pytest по всем модулям (91 тест)
make format        # ruff format + ruff --fix
make up / down     # docker compose
make migrate       # alembic upgrade head
make clean         # удалить кеши
```

## Тесты

- `shared/` — 4 теста схем/enum'ов
- `xui_client/` — 25 тестов, сеть замокана через `pytest-httpx`
- `backend/` — 34 теста, `XUIClient` мокается через `AsyncMock(spec=XUIClientProtocol)`
- `bot/` — 28 тестов, `BackendClient` через `pytest-httpx`

Для реальной 3x-ui панели или Telegram никакие тесты **не требуются** — всё моках.

## Контракты (source of truth)

| Что                        | Файл                                      |
|----------------------------|-------------------------------------------|
| HTTP API backend ↔ bot     | `shared/shared/contracts/http.py`         |
| Python API backend ↔ xui   | `shared/shared/contracts/xui.py`          |
| Иерархия ошибок            | `shared/shared/contracts/errors.py`       |
| Pydantic DTO               | `shared/shared/schemas/`                  |
| Enums (статусы, провайдеры)| `shared/shared/enums.py`                  |

Аутентификация между сервисами:
- `X-Bot-Token` — обязателен на всех `/api/v1/*` кроме webhook'ов
- `X-Admin-Token` — дополнительно на `/api/v1/admin/*`
- webhook'и платежей (`/api/v1/payments/webhook/{provider}`) — без токена, подпись проверяется адаптером

## Платежи

Подключено 3 адаптера, все реализуют `PaymentProviderAdapter` Protocol:

- **YooKassa** (RUB) — `YOOKASSA_SHOP_ID` + `YOOKASSA_SECRET_KEY`
- **CryptoBot** (USDT и др.) — `CRYPTOBOT_TOKEN`, HMAC SHA256 для webhook'а
- **Test** — мгновенно помечает платёж как succeeded, удобно для dev

Добавить новый адаптер: реализуй `PaymentProviderAdapter` в `backend/backend/payments/`, зарегистрируй в `factory.py`, добавь enum-значение в `shared/shared/enums.PaymentProvider` (breaking change в shared).

## Интеграция с 3x-ui

`xui_client.XUIClient` полностью удовлетворяет `shared.contracts.xui.XUIClientProtocol`:

- `create_vless_client` — идемпотентно по email или префиксу `tg_{telegram_id}_*`
- `disable/enable/delete/extend_client`
- `get_client_traffic`, `reset_client_traffic`
- `list_inbounds`, `health_check`
- VLESS-ссылка: Reality (`pbk/sid/sni/fp/spx`) и TLS (`sni/fp/alpn`) + tcp/ws/grpc/h2
- QR: `qrcode[pil]` → PNG bytes
- Auto re-login при 401 через `tenacity`
- Все сетевые ошибки оборачиваются в `shared.contracts.errors.XUIError`

## История сессий

Скелет и оркестрация — главная Devin-сессия.
Модули реализованы параллельно тремя дочерними сессиями:

- **xui_client** — [PR #2](https://github.com/Goldinflam/vpn-shop-bot/pull/2)
- **bot** — [PR #1](https://github.com/Goldinflam/vpn-shop-bot/pull/1)
- **backend** — [PR #3](https://github.com/Goldinflam/vpn-shop-bot/pull/3)
- **shared fix** — [PR #4](https://github.com/Goldinflam/vpn-shop-bot/pull/4)

## Лицензия

Приватный проект.
