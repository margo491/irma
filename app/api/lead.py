from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
import httpx
from app.config import settings
from app.database import get_db
from app.schemas.lead import LeadCreate, LeadOut
from app.services.lead import create_lead

router = APIRouter()


@router.post("/", response_model=LeadOut)
async def new_lead(data: LeadCreate, db: AsyncSession = Depends(get_db)):
    digits = "".join(c for c in data.phone if c.isdigit())
    if len(digits) < 10:
        raise HTTPException(status_code=422, detail="Неверный номер телефона")

    lead = await create_lead(db, data)

    if settings.admin_max_user_id:
        text = (
            f"📝 Новая заявка с сайта ({data.source})\n"
            f"Имя: {data.name}\n"
            f"Телефон: {data.phone}\n"
            + (f"Почта: {data.email}\n" if data.email else "")
        )
        async with httpx.AsyncClient() as client:
            await client.post(
                "https://botapi.max.ru/messages",
                params={"user_id": settings.admin_max_user_id},
                headers={"Authorization": settings.max_token},
                json={"text": text},
                timeout=10,
            )

    return lead
