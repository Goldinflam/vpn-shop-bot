"""HTTP contract between `bot` and `backend`.

This module is the source of truth for URL shapes and auth headers. Both
the backend router and the bot HTTP client must match these constants.

Auth:
    - Every bot->backend request MUST send header ``X-Bot-Token``.
    - Admin-only endpoints additionally require ``X-Admin-Token``.
    - Payment provider webhooks are unauthenticated at HTTP level; the
      backend verifies provider-specific signatures inside each handler.

Base path: ``/api/v1``.

Each constant's docstring describes method, body DTO, and response DTO.
"""

from typing import Final

API_PREFIX: Final[str] = "/api/v1"

# --- bot <-> backend ---
#: POST body=UserUpsert -> UserOut
USERS_UPSERT: Final[str] = "/users"
#: GET -> UserOut
USER_GET: Final[str] = "/users/{telegram_id}"
#: GET -> list[SubscriptionOut]
USER_SUBSCRIPTIONS: Final[str] = "/users/{telegram_id}/subscriptions"

#: GET -> list[PlanOut]
PLANS_LIST: Final[str] = "/plans"
#: GET -> PlanOut
PLAN_GET: Final[str] = "/plans/{plan_id}"

#: POST body=PaymentCreate -> PaymentOut
PAYMENTS_CREATE: Final[str] = "/payments"
#: GET -> PaymentOut
PAYMENT_GET: Final[str] = "/payments/{payment_id}"

#: GET -> SubscriptionOut
SUBSCRIPTION_GET: Final[str] = "/subscriptions/{subscription_id}"
#: POST body=SubscriptionRenew -> PaymentOut
SUBSCRIPTION_RENEW: Final[str] = "/subscriptions/{subscription_id}/renew"
#: GET -> image/png
SUBSCRIPTION_QR: Final[str] = "/subscriptions/{subscription_id}/qr"
#: GET -> IssuedVpnOut
SUBSCRIPTION_ISSUED: Final[str] = "/subscriptions/{subscription_id}/issued"

# --- trial & promo ---
#: POST body=TrialCreateIn -> IssuedVpnOut
TRIAL_CREATE: Final[str] = "/trial/create"
#: POST body=PromoApplyIn -> PromoApplyOut
PROMO_APPLY: Final[str] = "/promo/apply"

# --- webhooks (unauthenticated, provider-signed) ---
#: POST raw provider body -> 200
PAYMENT_WEBHOOK: Final[str] = "/payments/webhook/{provider}"

# --- admin ---
ADMIN_PLANS: Final[str] = "/admin/plans"
ADMIN_PLAN: Final[str] = "/admin/plans/{plan_id}"
ADMIN_STATS: Final[str] = "/admin/stats"
ADMIN_BROADCAST: Final[str] = "/admin/broadcast"

# --- header names (not secrets — they are HTTP header field names) ---
HEADER_BOT_TOKEN: Final[str] = "X-Bot-Token"  # noqa: S105
HEADER_ADMIN_TOKEN: Final[str] = "X-Admin-Token"  # noqa: S105
