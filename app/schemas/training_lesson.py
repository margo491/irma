from pydantic import BaseModel


class TrainingLessonOut(BaseModel):
    id: int
    slug: str
    tag: str
    title: str
    subtitle: str
    price_label: str | None
    image_path: str | None
    section1_heading: str | None
    section1_items: list[str]
    section2_heading: str | None
    section2_items: list[str]
    bonus_note: str | None
