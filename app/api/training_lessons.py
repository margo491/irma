from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import get_db
from app.models.training_lesson import TrainingLesson
from app.schemas.training_lesson import TrainingLessonOut

router = APIRouter()


def _split(text: str | None) -> list[str]:
    if not text:
        return []
    return [line.strip() for line in text.splitlines() if line.strip()]


def _to_out(lesson: TrainingLesson) -> TrainingLessonOut:
    return TrainingLessonOut(
        id=lesson.id,
        slug=lesson.slug,
        tag=lesson.tag,
        title=lesson.title,
        subtitle=lesson.subtitle,
        price_label=lesson.price_label,
        image_path=lesson.image_path,
        section1_heading=lesson.section1_heading,
        section1_items=_split(lesson.section1_items),
        section2_heading=lesson.section2_heading,
        section2_items=_split(lesson.section2_items),
        bonus_note=lesson.bonus_note,
    )


@router.get("/", response_model=list[TrainingLessonOut])
async def list_lessons(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(TrainingLesson).order_by(TrainingLesson.created_at.desc()))
    return [_to_out(lesson) for lesson in result.scalars().all()]


@router.get("/{slug}", response_model=TrainingLessonOut)
async def get_lesson(slug: str, db: AsyncSession = Depends(get_db)):
    item = await db.scalar(select(TrainingLesson).where(TrainingLesson.slug == slug))
    if not item:
        raise HTTPException(status_code=404, detail="Lesson not found")
    return _to_out(item)
