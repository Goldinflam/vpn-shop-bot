from enum import StrEnum


class SubscriptionStatus(StrEnum):
    PENDING = "pending"
    ACTIVE = "active"
    EXPIRED = "expired"
    DISABLED = "disabled"


class PaymentStatus(StrEnum):
    PENDING = "pending"
    SUCCEEDED = "succeeded"
    CANCELED = "canceled"
    FAILED = "failed"


class PaymentProvider(StrEnum):
    YOOKASSA = "yookassa"
    CRYPTOBOT = "cryptobot"
    TELEGRAM_STARS = "telegram_stars"
    TEST = "test"


class Currency(StrEnum):
    RUB = "RUB"
    USD = "USD"
    USDT = "USDT"
    XTR = "XTR"  # Telegram Stars


class Locale(StrEnum):
    RU = "ru"
    EN = "en"
