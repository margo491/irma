from decimal import Decimal
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.menu import MenuItem
from app.models.order import Order
from app.models.user import User
from app.schemas.order import OrderCreate, OrderItem
from app.services.bonus import earn_bonuses, spend_bonuses


async def create_order(db: AsyncSession, data: OrderCreate) -> Order:
    user = await db.get(User, data.user_id)
    if not user:
        raise ValueError(f"Пользователь {data.user_id} не найден")

    total = Decimal("0")
    order_items = []
    for ref in data.items:
        item = await db.get(MenuItem, ref.item_id)
        if not item or not item.is_available:
            raise ValueError(f"Позиция {ref.item_id} недоступна")
        line_total = Decimal(str(item.price)) * ref.qty
        total += line_total
        order_items.append({"item_id": item.id, "name": item.name, "qty": ref.qty, "price": str(item.price)})

    order = Order(
        user_id=user.id,
        items=order_items,
        total_amount=total,
        bonuses_used=Decimal("0"),
        bonuses_earned=Decimal("0"),
        status="created",
    )
    db.add(order)
    await db.flush()  # получить order.id до транзакций

    if data.bonuses_to_spend > 0:
        spent = await spend_bonuses(db, user, order, data.bonuses_to_spend)
        order.bonuses_used = spent
        order.total_amount = total - spent

    earned = await earn_bonuses(db, user, order)
    order.bonuses_earned = earned

    await db.commit()
    await db.refresh(order)
    return order


async def repeat_order(db: AsyncSession, order_id: int, user_id: int) -> tuple[Order, list[int]]:
    """Создаёт новый заказ по составу старого. Возвращает (заказ, список недоступных item_id)."""
    original = await db.get(Order, order_id)
    if not original or original.user_id != user_id:
        raise ValueError("Заказ не найден")

    unavailable_ids = []
    valid_items = []
    for ref in original.items:
        item = await db.get(MenuItem, ref["item_id"])
        if not item or not item.is_available:
            unavailable_ids.append(ref["item_id"])
        else:
            valid_items.append(OrderItem(item_id=ref["item_id"], qty=ref["qty"]))

    new_order = await create_order(
        db, OrderCreate(user_id=user_id, items=valid_items)
    )
    return new_order, unavailable_ids
