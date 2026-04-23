# Telegram Bot Agent — Техническое задание

> Этот файл — источник правды для дочерней Devin-сессии, работающей только в папке `bot/`.
> Не редактируй файлы вне `bot/`, кроме как через PR в `shared/contracts/http.py` (если нашёл баг).

## Область ответственности
Telegram-бот на aiogram 3.x: пользовательский интерфейс, FSM, i18n, админ-команды.

## Жёсткие правила
1. **НИКОГДА** не обращайся к БД напрямую. Весь стейт — через backend HTTP API (контракт: `shared/shared/contracts/http.py`).
2. **НИКОГДА** не импортируй `py3xui` или `xui_client`. VPN-операции — через backend.
3. Каждый исходящий запрос к backend — с заголовком `X-Bot-Token`.
4. Админ-команды (`/stats`, `/broadcast`, админ-меню) — дополнительно слать `X-Admin-Token`.

## Стек
- aiogram 3.7+ (async, `Dispatcher`, `Router`, FSM)
- aiogram-i18n или babel для i18n (ru/en, дефолт ru)
- httpx.AsyncClient — клиент к backend
- pydantic-settings для конфига

## Структура
```
bot/
├── bot/
│   ├── __init__.py
│   ├── __main__.py          # точка входа: python -m bot
│   ├── config.py            # pydantic-settings
│   ├── api_client/
│   │   ├── __init__.py      # BackendClient
│   │   └── errors.py
│   ├── handlers/
│   │   ├── start.py
│   │   ├── buy.py           # FSM: выбор тарифа → оплата
│   │   ├── my_subs.py
│   │   ├── help.py
│   │   ├── admin.py
│   │   └── common.py
│   ├── keyboards/
│   │   ├── inline.py
│   │   └── reply.py
│   ├── middlewares/
│   │   ├── user_upsert.py   # на каждое сообщение — POST /users
│   │   ├── i18n.py
│   │   └── throttle.py
│   ├── states/
│   │   └── buy.py
│   ├── locales/
│   │   ├── ru/LC_MESSAGES/messages.po
│   │   └── en/LC_MESSAGES/messages.po
│   └── utils/
│       └── vpn_instructions.py   # тексты инструкций по ОС
├── tests/
│   ├── test_api_client.py
│   └── test_handlers.py
└── pyproject.toml
```

## Сценарии пользователя
1. `/start` → приветствие, главное меню (Купить / Мои подписки / Помощь / Язык).
2. **Купить**: список тарифов → выбор → выбор провайдера оплаты (YooKassa / CryptoBot) → POST /payments → показать ссылку/invoice. После успеха (бот получит колбэк от backend? нет — polling `GET /users/{tg}/subscriptions`) — показать VLESS-ссылку + QR + инструкции.
3. **Мои подписки**: список, каждая — с кнопками «Показать ссылку», «Инструкция», «Продлить».
4. **Помощь**: выбор ОС (Android/iOS/Windows/macOS) → текст с deep-links на клиенты (v2rayNG, Hiddify, Happ, FoXray и т.п.).
5. **Язык**: переключение локали (сохраняется через PATCH профиля — реально в рамках MVP можно держать в памяти + при upsert).

## Админ-команды
- `/stats` — выводит сводку (вызов `GET /admin/stats`).
- `/broadcast` (FSM) — массовая рассылка (вызов `POST /admin/broadcast` — эндпоинт может быть добавлен в shared при согласовании).
- Фильтр `F.from_user.id.in_(settings.admin_ids)`.

## BackendClient
Класс в `bot/api_client/__init__.py`:
```python
class BackendClient:
    def __init__(self, base_url: str, bot_token: str, admin_token: str | None = None) -> None: ...
    async def upsert_user(self, dto: UserUpsert) -> UserOut: ...
    async def list_plans(self) -> list[PlanOut]: ...
    async def user_subscriptions(self, telegram_id: int) -> list[SubscriptionOut]: ...
    async def create_payment(self, dto: PaymentCreate) -> PaymentOut: ...
    async def get_subscription(self, sub_id: int) -> SubscriptionOut: ...
    async def renew_subscription(self, sub_id: int, dto: SubscriptionRenew) -> PaymentOut: ...
    # admin
    async def admin_stats(self) -> dict[str, Any]: ...
```
Ошибки backend'а должны конвертиться в `BackendError`/`NotFoundError`/и т.п. из `bot.api_client.errors`.

## i18n
Минимум: ru + en. Все пользовательские строки через `L[...]`/`_("...")`. На `/start` определяй язык по `message.from_user.language_code` (если ru/uk/be → ru; иначе en), сохраняй в профиле.

## QR-код
Получай от backend (`GET /subscriptions/{id}/qr` → `image/png` либо base64 в `SubscriptionOut`). Не генерь QR сам.

## Тесты
- Unit для `BackendClient`: замокай backend через `pytest-httpx` с эндпоинтами из `shared/contracts/http.py`.
- Smoke для 2-3 хендлеров через `aiogram.methods` + `MockedBot` (опционально — можно оставить как TODO, но хотя бы 1 пример).

## Качество
- `ruff check bot/` и `mypy bot/ --strict` — чисто.
- Нет прямых SQL/HTTP-вызовов к 3x-ui.

## Готовность
1. `python -m bot` стартует polling при валидном `BOT_TOKEN`.
2. Все пункты главного меню работают (при наличии backend).
3. i18n ru/en переключается.
4. `pytest bot/ -v` зелёный.
5. Dockerfile собирается.
6. PR в ветку `agent/bot` на базе `main`, заголовок `[bot] initial implementation`.
