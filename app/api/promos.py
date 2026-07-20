from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import get_db
from app.models.promo import Promo
from app.schemas.promo import PromoOut

router = APIRouter()


@router.get("/", response_model=list[PromoOut])
async def list_promos(limit: int = Query(50, le=100), db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Promo).order_by(Promo.created_at.asc()).limit(limit))
    return result.scalars().all()
