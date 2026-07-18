from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import get_db
from app.models.news import News
from app.schemas.news import NewsOut

router = APIRouter()


@router.get("/", response_model=list[NewsOut])
async def list_news(limit: int = Query(50, le=100), db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(News).order_by(News.published_at.desc()).limit(limit))
    return result.scalars().all()


@router.get("/{news_id}", response_model=NewsOut)
async def get_news(news_id: int, db: AsyncSession = Depends(get_db)):
    item = await db.get(News, news_id)
    if not item:
        raise HTTPException(status_code=404, detail="News not found")
    return item
