from decimal import Decimal

from shared.enums import Currency, PaymentProvider, SubscriptionStatus
from shared.schemas import PaymentCreate, PlanOut, UserUpsert


def test_user_upsert_validates_telegram_id() -> None:
    u = UserUpsert(telegram_id=123, username="x")
    assert u.telegram_id == 123


def test_plan_out_defaults() -> None:
    p = PlanOut(id=1, name="1 month", duration_days=30, traffic_gb=0, price=Decimal("299"))
    assert p.currency == Currency.RUB
    assert p.is_active is True


def test_payment_create_enum() -> None:
    pc = PaymentCreate(telegram_id=1, plan_id=1, provider=PaymentProvider.YOOKASSA)
    assert pc.provider == PaymentProvider.YOOKASSA


def test_subscription_status_values() -> None:
    assert SubscriptionStatus.ACTIVE.value == "active"
    assert set(SubscriptionStatus) == {
        SubscriptionStatus.PENDING,
        SubscriptionStatus.ACTIVE,
        SubscriptionStatus.EXPIRED,
        SubscriptionStatus.DISABLED,
    }
