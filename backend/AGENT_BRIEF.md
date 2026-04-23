# Backend Agent — Техническое задание

> Этот файл — источник правды для дочерней Devin-сессии, работающей только в папке `backend/`.
> Не редактируй файлы вне `backend/`, кроме как через PR в `shared/` (с чётким обоснованием).

## Область ответственности
FastAPI-сервис: пользователи, тарифы, подписки, платежи. Вся бизнес-логика.

## Не твоя область
- `xui_client/` — это готовая библиотека. Импортируй `from xui_client import XUIClient` и вызывай её методы (контракт: `shared/shared/contracts/xui.py`). **Не** обращайся к `py3xui` напрямую.
- `bot/` — не трогай.
- `shared/` — можно дополнять схемы/контракты, но **только** если согласовано с остальными агентами (в PR опиши breaking change).

## Стек
- FastAPI 0.111+, Uvicorn
- SQLAlchemy 2.x (async) + Alembic
- Драйверы: asyncpg (prod), aiosqlite (dev/tests)
- Pydantic v2, pydantic-settings
- APScheduler для крона
- yookassa SDK, aiocryptopay (CryptoBot)
- pytest + pytest-asyncio + pytest-httpx

## Обязательные HTTP-эндпоинты
Все URL и заголовки — в `shared/shared/contracts/http.py`. Реализуй строго их. Префикс `/api/v1`.

Аутентификация:
- Все bot→backend эндпоинты требуют `X-Bot-Token: {BOT_API_TOKEN}`.
- Админ-эндпоинты дополнительно требуют `X-Admin-Token: {ADMIN_API_TOKEN}`.
- Вебхуки платежей — без `X-Bot-Token`; подпись проверяется провайдер-специфично.

## Модели БД (SQLAlchemy)
Минимум:

### User
`id, telegram_id (unique), username, first_name, last_name, locale, balance (Numeric 12,2), is_admin, is_banned, created_at, updated_at`

### Plan
`id, name, description, duration_days, traffic_gb (0=unlimited), price (Numeric 12,2), currency, is_active, sort_order, created_at, updated_at`

### Subscription
`id, user_id (FK), plan_id (FK), xui_client_uuid, xui_inbound_id, xui_email (unique), vless_link (Text), traffic_limit_bytes, traffic_used_bytes, starts_at, expires_at, status, created_at, updated_at`

### Payment
`id, user_id (FK), plan_id (FK), subscription_id (FK, nullable), amount (Numeric 12,2), currency, provider, provider_payment_id, payment_url, status, raw_payload (JSONB), created_at, updated_at`

Все Numeric → `Decimal`. Используй `server_default=func.now()` и `onupdate=func.now()`.
Настрой Alembic с initial migration.

## Сервисный слой
- `UserService.upsert(dto: UserUpsert) -> UserOut`
- `PlanService.list_active() -> list[PlanOut]`, CRUD для админки
- `SubscriptionService.create_from_payment(payment: Payment) -> Subscription` — вызывает `XUIClient.create_vless_client`, сохраняет vless_link/uuid/email.
- `SubscriptionService.expire_overdue()` — крон, раз в 5 минут, помечает expired + вызывает `xui_client.disable_client`.
- `PaymentService.create(dto: PaymentCreate) -> PaymentOut` — роутит по provider в соответствующий `PaymentProviderAdapter`.
- `PaymentService.handle_webhook(provider, raw_body, headers)` — валидирует подпись, если status=succeeded → `SubscriptionService.create_from_payment`.

## Провайдеры платежей
Интерфейс:
```python
class PaymentProviderAdapter(Protocol):
    async def create(self, payment: Payment, plan: Plan, user: User) -> PaymentCreatedResult: ...  # payment_url + provider_payment_id
    async def verify_webhook(self, body: bytes, headers: Mapping[str, str]) -> WebhookVerificationResult: ...  # succeeded|canceled|failed + provider_payment_id
```
Реализуй:
- `YooKassaAdapter` (через SDK `yookassa`)
- `CryptoBotAdapter` (через `aiocryptopay`)
- `TestAdapter` — без внешних вызовов, для интеграционных тестов

## Конфигурация
Через `pydantic-settings`, читай `.env`. Обязательные переменные описаны в корневом `.env.example`.

## Формирование VLESS-ссылки и QR
Не сам. Вызови `XUIClient.create_vless_client(...)` — он вернёт `VlessClientResult` с готовыми `vless_link` и `qr_png`. Если `qr_png` нужно вернуть боту — отдавай через `GET /subscriptions/{id}/qr` как `image/png`, либо base64 в JSON.

## Тесты
- Unit: сервисы на in-memory SQLite.
- API: `httpx.AsyncClient` + `ASGITransport`. Проверь все роуты, заголовки, коды ошибок.
- Платежи: мок HTTP провайдеров (pytest-httpx).
- `XUIClient` в тестах — мок через `unittest.mock.AsyncMock`, реализующий `XUIClientProtocol`.

## Качество
- `ruff check backend/` и `mypy backend/` в `--strict` должны проходить.
- Покрытие сервисного слоя — 80%+.
- Нет `Any`, `getattr`, `setattr`.

## Готовность
1. Все эндпоинты из `shared/shared/contracts/http.py` реализованы.
2. `alembic upgrade head` создаёт БД с нуля.
3. `uvicorn backend.main:app` стартует, `/health` возвращает 200.
4. `pytest backend/ -v` зелёный.
5. Dockerfile собирается; `docker-compose up backend` работает с дефолтным .env.
6. PR в ветку `agent/backend` на базе `main`, заголовок `[backend] initial implementation`.
