"""FastAPI routers."""

from backend.routers.admin import router as admin_router
from backend.routers.admin_servers import router as admin_servers_router
from backend.routers.health import router as health_router
from backend.routers.payments import router as payments_router
from backend.routers.plans import router as plans_router
from backend.routers.promos import router as promos_router
from backend.routers.subscription_public import router as subscription_public_router
from backend.routers.subscriptions import router as subscriptions_router
from backend.routers.users import router as users_router

__all__ = [
    "admin_router",
    "admin_servers_router",
    "health_router",
    "payments_router",
    "plans_router",
    "promos_router",
    "subscription_public_router",
    "subscriptions_router",
    "users_router",
]
