from datetime import datetime
from pydantic import BaseModel, ConfigDict


class NewsOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    tag: str
    title: str
    text: str
    image_path: str | None
    published_at: datetime
