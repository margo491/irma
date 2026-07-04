from pydantic import BaseModel
from datetime import datetime


class LeadCreate(BaseModel):
    name: str
    phone: str
    email: str | None = None
    source: str = "site"


class LeadOut(BaseModel):
    id: int
    name: str
    phone: str
    email: str | None
    source: str
    status: str
    created_at: datetime

    model_config = {"from_attributes": True}
