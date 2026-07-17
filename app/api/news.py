from fastapi import APIRouter, Depends, Query
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
