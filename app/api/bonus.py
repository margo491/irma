from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.database import get_db
from app.models.user import User
from app.models.bonus_transaction import BonusTransaction
from app.schemas.bonus import BonusBalanceOut

router = APIRouter()


@router.get("/{user_id}", response_model=BonusBalanceOut)
async def get_bonuses(user_id: int, db: AsyncSession = Depends(get_db)):
    user = await db.get(User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="Пользователь не найден")

    result = await db.execute(
        select(BonusTransaction)
        .where(BonusTransaction.user_id == user_id)
        .order_by(BonusTransaction.created_at.desc())
        .limit(20)
    )
    return BonusBalanceOut(
        user_id=user_id,
        balance=user.bonus_balance,
        transactions=result.scalars().all(),
    )
