"""FastAPI routers."""

from backend.routers.admin import router as admin_router
from backend.routers.health import router as health_router
from backend.routers.payments import router as payments_router
from backend.routers.plans import router as plans_router
from backend.routers.subscriptions import router as subscriptions_router
from backend.routers.users import router as users_router

__all__ = [
    "admin_router",
    "health_router",
    "payments_router",
    "plans_router",
    "subscriptions_router",
    "users_router",
]
