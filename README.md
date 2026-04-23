# VPN Shop Bot

Telegram-бот для продажи VPN-подписок с интеграцией 3x-ui.

## Архитектура

Монорепо из трёх независимых модулей + общий пакет контрактов:

```
vpn-shop-bot/
├── shared/        Pydantic-схемы / DTO / enums — контракты между модулями
├── xui_client/    Обёртка над py3xui под домен проекта
├── backend/       FastAPI: users, plans, subscriptions, payments
└── bot/           aiogram 3.x: Telegram UI, FSM, i18n
```

Каждый модуль — независимый Python-пакет с собственным `pyproject.toml`.
Все три зависят от `shared/`.

## Стек

- Python 3.11
- aiogram 3.x (bot)
- FastAPI + Uvicorn (backend)
- SQLAlchemy 2.x + Alembic + PostgreSQL (dev: SQLite)
- py3xui (xui_client)
- Pydantic v2
- Docker + docker-compose
- ruff + mypy + pytest

## Быстрый старт (dev)

```bash
cp .env.example .env
# отредактируйте .env — в минимуме нужен BOT_TOKEN

docker-compose up --build
```

## Разработка

```bash
make install       # установить все 4 пакета в editable-режиме
make lint          # ruff + mypy
make test          # pytest по всем модулям
make format        # ruff format
```

## Контракты

Все межмодульные контракты зафиксированы в `shared/` — любое изменение
поля/эндпоинта начинается с PR в `shared/`.

- HTTP API backend ↔ bot: см. `shared/shared/contracts/http.py`
- Python API backend ↔ xui_client: см. `shared/shared/contracts/xui.py`
- Схемы БД (DTO-образы): см. `shared/shared/schemas/`
