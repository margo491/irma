from datetime import datetime
from pydantic import BaseModel, ConfigDict


class BlogPostOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    tag: str
    title: str
    excerpt: str
    text: str
    image_path: str | None
    published_at: datetime
