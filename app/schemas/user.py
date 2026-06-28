from pydantic import BaseModel
from datetime import date, datetime
from decimal import Decimal


class UserCreate(BaseModel):
    external_id: str
    name: str
    birth_date: date | None = None


class UserUpdate(BaseModel):
    name: str | None = None
    birth_date: date | None = None


class UserOut(BaseModel):
    id: int
    external_id: str
    name: str
    birth_date: date | None
    bonus_balance: Decimal
    created_at: datetime

    model_config = {"from_attributes": True}
