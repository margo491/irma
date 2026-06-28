from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.database import get_db
from app.models.user import User
from app.schemas.user import UserCreate, UserUpdate, UserOut

router = APIRouter()


@router.post("/", response_model=UserOut)
async def upsert_user(data: UserCreate, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(User).where(User.external_id == data.external_id))
    user = result.scalar_one_or_none()
    if user:
        user.name = data.name
        if data.birth_date:
            user.birth_date = data.birth_date
    else:
        user = User(**data.model_dump())
        db.add(user)
    await db.commit()
    await db.refresh(user)
    return user


@router.patch("/{external_id}", response_model=UserOut)
async def update_user(external_id: str, data: UserUpdate, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(User).where(User.external_id == external_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="Пользователь не найден")
    if data.name is not None:
        user.name = data.name
    if data.birth_date is not None:
        user.birth_date = data.birth_date
    await db.commit()
    await db.refresh(user)
    return user


@router.get("/{external_id}", response_model=UserOut)
async def get_user(external_id: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(User).where(User.external_id == external_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="Пользователь не найден")
    return user
