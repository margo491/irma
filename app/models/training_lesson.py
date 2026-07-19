from datetime import datetime
from sqlalchemy import String, Text, DateTime, func
from sqlalchemy.orm import Mapped, mapped_column
from app.database import Base


class TrainingLesson(Base):
    __tablename__ = "training_lessons"

    id: Mapped[int] = mapped_column(primary_key=True)
    slug: Mapped[str] = mapped_column(String, unique=True, nullable=False)
    tag: Mapped[str] = mapped_column(String, default="Видеоурок")
    title: Mapped[str] = mapped_column(String, nullable=False)
    subtitle: Mapped[str] = mapped_column(Text, default="")
    price_label: Mapped[str | None] = mapped_column(String, nullable=True)
    image_path: Mapped[str | None] = mapped_column(String, nullable=True)
    section1_heading: Mapped[str | None] = mapped_column(String, nullable=True)
    section1_items: Mapped[str] = mapped_column(Text, default="")
    section2_heading: Mapped[str | None] = mapped_column(String, nullable=True)
    section2_items: Mapped[str] = mapped_column(Text, default="")
    bonus_note: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
