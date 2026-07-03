from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
import httpx
from app.config import settings
from app.database import get_db
from app.models.order import Order
from app.schemas.order import OrderCreate, OrderOut
from app.services.order import create_order, repeat_order

router = APIRouter()
history_router = APIRouter()


@router.post("/", response_model=OrderOut)
async def new_order(data: OrderCreate, db: AsyncSession = Depends(get_db)):
    try:
        return await create_order(db, data)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/{order_id}/repeat")
async def repeat(order_id: int, user_id: int, db: AsyncSession = Depends(get_db)):
    try:
        new_order, unavailable = await repeat_order(db, order_id, user_id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return {"order": new_order, "unavailable_item_ids": unavailable}


class LandingItem(BaseModel):
    name: str
    price: int
    qty: int

class LandingOrder(BaseModel):
    phone: str
    items: list[LandingItem]


@router.post("/landing")
async def landing_order(data: LandingOrder):
    digits = "".join(c for c in data.phone if c.isdigit())
    if len(digits) < 10:
        raise HTTPException(status_code=422, detail="Неверный номер телефона")
    if not settings.admin_max_user_id:
        return {"ok": True}
    items_text = "\n".join(
        f"  • {i.name} × {i.qty} = {i.price * i.qty} ₽" for i in data.items
    )
    total = sum(i.price * i.qty for i in data.items)
    text = (
        f"🛒 Новый заказ с сайта\n"
        f"Телефон: {data.phone}\n\n"
        f"Состав:\n{items_text}\n\n"
        f"Итого: {total} ₽"
    )
    async with httpx.AsyncClient() as client:
        await client.post(
            "https://botapi.max.ru/messages",
            params={"user_id": settings.admin_max_user_id},
            headers={"Authorization": settings.max_token},
            json={"text": text},
            timeout=10,
        )
    return {"ok": True}


@history_router.get("/{user_id}", response_model=list[OrderOut])
async def get_order_history(user_id: int, limit: int = 10, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(Order)
        .where(Order.user_id == user_id)
        .order_by(Order.created_at.desc())
        .limit(min(limit, 10))
    )
    return result.scalars().all()
