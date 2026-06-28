from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.database import get_db
from app.models.menu import MenuCategory, MenuItem
from app.schemas.menu import CategoryOut, MenuItemOut

router = APIRouter()
items_router = APIRouter()


@router.get("/", response_model=list[CategoryOut])
async def get_categories(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(MenuCategory).order_by(MenuCategory.sort_order))
    return result.scalars().all()


@router.get("/{category_id}", response_model=list[MenuItemOut])
async def get_items_by_category(category_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(MenuItem).where(MenuItem.category_id == category_id, MenuItem.is_available == True)
    )
    return result.scalars().all()


@items_router.get("/{item_id}", response_model=MenuItemOut)
async def get_item(item_id: int, db: AsyncSession = Depends(get_db)):
    item = await db.get(MenuItem, item_id)
    if not item:
        raise HTTPException(status_code=404, detail="Позиция не найдена")
    return item
