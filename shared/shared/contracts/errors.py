"""Exception hierarchy shared between modules.

`xui_client` and `backend` MUST raise these so the bot can react uniformly.
"""


class VPNShopError(Exception):
    """Base class for all domain errors."""


# --- xui_client ---
class XUIError(VPNShopError):
    """Generic x-ui panel error."""


class XUIAuthError(XUIError):
    """Auth/session failure against x-ui."""


class XUIClientNotFoundError(XUIError):
    """Client (email/uuid) not found in panel."""


class XUIInboundNotFoundError(XUIError):
    """Inbound id not present in panel."""


# --- backend / domain ---
class NotFoundError(VPNShopError):
    """Requested entity does not exist."""


class AlreadyExistsError(VPNShopError):
    """Entity with the same unique key already exists."""


class PaymentError(VPNShopError):
    """Generic payment flow failure."""


class PaymentProviderError(PaymentError):
    """Error returned by an external payment provider."""


class SubscriptionError(VPNShopError):
    """Subscription-related business error."""
