from pydantic import BaseModel
from datetime import datetime
from decimal import Decimal


class OrderItem(BaseModel):
    item_id: int
    qty: int


class OrderCreate(BaseModel):
    user_id: int
    items: list[OrderItem]
    bonuses_to_spend: Decimal = Decimal("0")


class OrderOut(BaseModel):
    id: int
    user_id: int
    items: list[dict]
    total_amount: Decimal
    bonuses_used: Decimal
    bonuses_earned: Decimal
    status: str
    created_at: datetime

    model_config = {"from_attributes": True}
