from pydantic import BaseModel
from datetime import datetime
from decimal import Decimal


class BonusTransactionOut(BaseModel):
    id: int
    user_id: int
    order_id: int | None
    type: str
    amount: Decimal
    created_at: datetime

    model_config = {"from_attributes": True}


class BonusBalanceOut(BaseModel):
    user_id: int
    balance: Decimal
    transactions: list[BonusTransactionOut] = []
