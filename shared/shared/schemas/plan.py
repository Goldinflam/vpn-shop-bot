from __future__ import annotations

from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field

from shared.enums import Currency


class PlanOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    description: str | None = None
    duration_days: int
    traffic_gb: int = Field(..., description="0 = unlimited")
    price: Decimal
    currency: Currency = Currency.RUB
    is_active: bool = True
    sort_order: int = 0


class PlanCreate(BaseModel):
    name: str
    description: str | None = None
    duration_days: int = Field(..., gt=0)
    traffic_gb: int = Field(..., ge=0)
    price: Decimal = Field(..., ge=0)
    currency: Currency = Currency.RUB
    is_active: bool = True
    sort_order: int = 0


class PlanUpdate(BaseModel):
    name: str | None = None
    description: str | None = None
    duration_days: int | None = Field(None, gt=0)
    traffic_gb: int | None = Field(None, ge=0)
    price: Decimal | None = Field(None, ge=0)
    currency: Currency | None = None
    is_active: bool | None = None
    sort_order: int | None = None
