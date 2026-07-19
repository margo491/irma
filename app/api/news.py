from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.config import settings
from app.database import get_db
from app.models.news import News
from app.schemas.news import NewsOut

router = APIRouter()


def _visible_cutoff() -> datetime:
    return datetime.utcnow() - timedelta(minutes=settings.news_publish_delay_minutes)


@router.get("/", response_model=list[NewsOut])
async def list_news(limit: int = Query(50, le=100), db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(News)
        .where(News.created_at <= _visible_cutoff())
        .order_by(News.published_at.desc())
        .limit(limit)
    )
    return result.scalars().all()


@router.get("/{news_id}", response_model=NewsOut)
async def get_news(news_id: int, db: AsyncSession = Depends(get_db)):
    item = await db.get(News, news_id)
    if not item or item.created_at > _visible_cutoff():
        raise HTTPException(status_code=404, detail="News not found")
    return item
