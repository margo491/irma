from pydantic import BaseModel, ConfigDict


class PromoOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    icon: str
    badge: str
    title: str
    text: str
