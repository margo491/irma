from decimal import Decimal
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.user import User
from app.models.order import Order
from app.models.bonus_transaction import BonusTransaction
from app.config import settings


async def earn_bonuses(db: AsyncSession, user: User, order: Order) -> Decimal:
    amount = (Decimal(str(order.total_amount)) * Decimal(str(settings.bonus_earn_rate))).quantize(
        Decimal("0.01")
    )
    db.add(BonusTransaction(user_id=user.id, order_id=order.id, type="earn", amount=amount))
    user.bonus_balance = Decimal(str(user.bonus_balance)) + amount
    return amount


async def spend_bonuses(db: AsyncSession, user: User, order: Order, requested: Decimal) -> Decimal:
    max_spend = (
        Decimal(str(order.total_amount)) * Decimal(str(settings.bonus_max_spend_rate))
    ).quantize(Decimal("0.01"))
    amount = min(requested, max_spend, Decimal(str(user.bonus_balance))).quantize(Decimal("0.01"))

    if amount <= 0:
        return Decimal("0")

    db.add(BonusTransaction(user_id=user.id, order_id=order.id, type="spend", amount=amount))
    user.bonus_balance = Decimal(str(user.bonus_balance)) - amount
    return amount
