"""Обработчики намерений бота. Каждый handler получает IncomingMessage и возвращает OutgoingMessage."""
import httpx
from app.bot.adapter import IncomingMessage, OutgoingMessage
from app.bot.intents import Intent

API_BASE = "http://localhost:8000"


async def handle(intent: Intent, msg: IncomingMessage, payload: dict) -> OutgoingMessage:
    match intent:
        case Intent.OPEN_MENU:
            return await _show_categories(msg)
        case Intent.OPEN_CATEGORY:
            return await _show_category(msg, payload.get("category_id"))
        case Intent.SHOW_PROFILE:
            return await _show_profile(msg)
        case Intent.SHOW_BONUSES:
            return await _show_bonuses(msg)
        case Intent.SHOW_ORDER_HISTORY:
            return await _show_history(msg)
        case Intent.REPEAT_ORDER:
            return await _repeat_order(msg, payload.get("order_id"))
        case _:
            return OutgoingMessage(
                user_id=msg.user_id,
                text="Не понял команду. Выберите пункт меню.",
                buttons=[
                    {"label": "Меню", "payload": {"intent": "open_menu"}},
                    {"label": "Профиль", "payload": {"intent": "show_profile"}},
                    {"label": "Бонусы", "payload": {"intent": "show_bonuses"}},
                    {"label": "История заказов", "payload": {"intent": "show_order_history"}},
                ],
            )


async def _show_categories(msg: IncomingMessage) -> OutgoingMessage:
    async with httpx.AsyncClient() as client:
        r = await client.get(f"{API_BASE}/menu/")
        categories = r.json()
    buttons = [{"label": c["name"], "payload": {"intent": "open_category", "category_id": c["id"]}} for c in categories]
    return OutgoingMessage(user_id=msg.user_id, text="Выберите категорию:", buttons=buttons)


async def _show_category(msg: IncomingMessage, category_id: int) -> OutgoingMessage:
    async with httpx.AsyncClient() as client:
        r = await client.get(f"{API_BASE}/menu/{category_id}")
        items = r.json()
    lines = [f"{i['name']} — {i['price']} ₽" for i in items]
    buttons = [{"label": f"Добавить: {i['name']}", "payload": {"intent": "add_item", "item_id": i["id"]}} for i in items]
    buttons.append({"label": "← Назад к категориям", "payload": {"intent": "open_menu"}})
    return OutgoingMessage(user_id=msg.user_id, text="\n".join(lines) or "Категория пуста", buttons=buttons)


async def _show_profile(msg: IncomingMessage) -> OutgoingMessage:
    async with httpx.AsyncClient() as client:
        r = await client.get(f"{API_BASE}/user/{msg.user_id}")
        if r.status_code == 404:
            return OutgoingMessage(user_id=msg.user_id, text="Профиль не найден. Введите ваше имя:")
        u = r.json()
    text = f"Имя: {u['name']}\nДата рождения: {u['birth_date'] or '—'}\nБонусы: {u['bonus_balance']} ₽"
    return OutgoingMessage(user_id=msg.user_id, text=text, buttons=[
        {"label": "Изменить имя", "payload": {"intent": "edit_name"}},
        {"label": "Изменить дату рождения", "payload": {"intent": "edit_birth_date"}},
    ])


async def _show_bonuses(msg: IncomingMessage) -> OutgoingMessage:
    async with httpx.AsyncClient() as client:
        ru = await client.get(f"{API_BASE}/user/{msg.user_id}")
        if ru.status_code == 404:
            return OutgoingMessage(user_id=msg.user_id, text="Профиль не найден.")
        user = ru.json()
        rb = await client.get(f"{API_BASE}/bonuses/{user['id']}")
        data = rb.json()
    return OutgoingMessage(user_id=msg.user_id, text=f"Ваш бонусный баланс: {data['balance']} ₽")


async def _show_history(msg: IncomingMessage) -> OutgoingMessage:
    async with httpx.AsyncClient() as client:
        ru = await client.get(f"{API_BASE}/user/{msg.user_id}")
        if ru.status_code == 404:
            return OutgoingMessage(user_id=msg.user_id, text="Профиль не найден.")
        user = ru.json()
        rh = await client.get(f"{API_BASE}/orders/{user['id']}")
        orders = rh.json()
    if not orders:
        return OutgoingMessage(user_id=msg.user_id, text="История заказов пуста.")
    lines = []
    buttons = []
    for o in orders:
        first_items = o["items"][:2]
        rest = len(o["items"]) - 2
        desc = ", ".join(i["name"] for i in first_items)
        if rest > 0:
            desc += f" и ещё {rest}"
        lines.append(f"{o['created_at'][:10]} — {o['total_amount']} ₽ ({desc})")
        buttons.append({"label": f"Повторить #{o['id']}", "payload": {"intent": "repeat_order", "order_id": o["id"]}})
    return OutgoingMessage(user_id=msg.user_id, text="\n".join(lines), buttons=buttons)


async def _repeat_order(msg: IncomingMessage, order_id: int) -> OutgoingMessage:
    async with httpx.AsyncClient() as client:
        ru = await client.get(f"{API_BASE}/user/{msg.user_id}")
        user = ru.json()
        r = await client.post(f"{API_BASE}/order/{order_id}/repeat", params={"user_id": user["id"]})
        data = r.json()
    text = f"Заказ повторён. Сумма: {data['order']['total_amount']} ₽"
    if data.get("unavailable_item_ids"):
        text += f"\nНедоступные позиции пропущены: {data['unavailable_item_ids']}"
    return OutgoingMessage(user_id=msg.user_id, text=text)
