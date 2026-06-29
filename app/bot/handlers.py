"""Обработчики намерений бота."""
from datetime import datetime
from decimal import Decimal
import httpx
from app.bot.adapter import IncomingMessage, OutgoingMessage
from app.bot.intents import Intent
from app.config import settings

API_BASE = "http://localhost:8000"

_sessions: dict[str, str] = {}
_session_data: dict[str, dict] = {}

# cart: user_id → {item_id: {"name": str, "price": Decimal, "qty": int}}
_carts: dict[str, dict[int, dict]] = {}

_MAIN_BUTTONS = [
    {"label": "Меню", "payload": {"intent": "open_menu"}},
    {"label": "Корзина", "payload": {"intent": "show_cart"}},
    {"label": "Профиль", "payload": {"intent": "show_profile"}},
    {"label": "Бонусы", "payload": {"intent": "show_bonuses"}},
    {"label": "История заказов", "payload": {"intent": "show_order_history"}},
]


async def handle(intent: Intent, msg: IncomingMessage, payload: dict) -> OutgoingMessage:
    state = _sessions.get(msg.user_id, "")

    if state == "awaiting_phone":
        return await _handle_awaiting_phone(msg)
    if state == "awaiting_birth":
        return await _handle_awaiting_birth(msg)

    async with httpx.AsyncClient() as client:
        r = await client.get(f"{API_BASE}/user/{msg.user_id}")
    if r.status_code == 404:
        name = msg.first_name or "Гость"
        _sessions[msg.user_id] = "awaiting_phone"
        _session_data[msg.user_id] = {"name": name}
        return OutgoingMessage(
            user_id=msg.user_id,
            text=(
                f"Привет, {name}! Рады видеть вас в боте Max-кафе.\n\n"
                "Введите ваш номер телефона для связи:"
            ),
        )

    match intent:
        case Intent.OPEN_MENU:
            return await _show_categories(msg)
        case Intent.OPEN_CATEGORY:
            return await _show_category(msg, payload.get("category_id"))
        case Intent.ADD_ITEM:
            return await _add_item(msg, payload.get("item_id"))
        case Intent.SHOW_CART:
            return await _show_cart(msg)
        case Intent.CLEAR_CART:
            _carts.pop(msg.user_id, None)
            return OutgoingMessage(
                user_id=msg.user_id,
                text="Корзина очищена.",
                buttons=[{"label": "Меню", "payload": {"intent": "open_menu"}}],
            )
        case Intent.CONFIRM_ORDER:
            return await _confirm_order(msg)
        case Intent.SHOW_PROFILE:
            return await _show_profile(msg)
        case Intent.SHOW_BONUSES:
            return await _show_bonuses(msg)
        case Intent.SHOW_ORDER_HISTORY:
            return await _show_history(msg)
        case Intent.REPEAT_ORDER:
            return await _repeat_order(msg, payload.get("order_id"))
        case _:
            return OutgoingMessage(user_id=msg.user_id, text="Выберите раздел:", buttons=_MAIN_BUTTONS)


async def _handle_awaiting_phone(msg: IncomingMessage) -> OutgoingMessage:
    phone = msg.text.strip()
    digits = "".join(c for c in phone if c.isdigit())
    if len(digits) < 10:
        return OutgoingMessage(
            user_id=msg.user_id,
            text="Не похоже на номер телефона. Введите номер в формате +7 (999) 123-45-67 или 89991234567:",
        )
    _session_data[msg.user_id]["phone"] = phone
    _sessions[msg.user_id] = "awaiting_birth"
    return OutgoingMessage(
        user_id=msg.user_id,
        text="Введите дату рождения (ДД.ММ.ГГГГ) — подарим бонусы ко дню рождения!\nИли отправьте «—» чтобы пропустить:",
    )


async def _handle_awaiting_birth(msg: IncomingMessage) -> OutgoingMessage:
    text = msg.text.strip()
    birth_date = None
    if text != "—":
        try:
            birth_date = datetime.strptime(text, "%d.%m.%Y").date().isoformat()
        except ValueError:
            return OutgoingMessage(
                user_id=msg.user_id,
                text="Неверный формат. Введите ДД.ММ.ГГГГ или «—» чтобы пропустить:",
            )

    data = _session_data.pop(msg.user_id, {})
    _sessions.pop(msg.user_id, None)
    name = data.get("name", "Гость")

    async with httpx.AsyncClient() as client:
        await client.post(
            f"{API_BASE}/user/",
            json={"external_id": msg.user_id, "name": name, "phone": data.get("phone"), "birth_date": birth_date},
        )

    return OutgoingMessage(
        user_id=msg.user_id,
        text=f"Профиль создан! Добро пожаловать, {name}!",
        buttons=_MAIN_BUTTONS,
    )


async def _show_categories(msg: IncomingMessage) -> OutgoingMessage:
    async with httpx.AsyncClient() as client:
        r = await client.get(f"{API_BASE}/menu/")
        categories = r.json()
    buttons = [
        {"label": c["name"], "payload": {"intent": "open_category", "category_id": c["id"]}}
        for c in categories
    ]
    cart = _carts.get(msg.user_id, {})
    if cart:
        total_qty = sum(v["qty"] for v in cart.values())
        buttons.append({"label": f"Корзина ({total_qty})", "payload": {"intent": "show_cart"}})
    return OutgoingMessage(user_id=msg.user_id, text="Выберите категорию:", buttons=buttons)


async def _show_category(msg: IncomingMessage, category_id: int) -> OutgoingMessage:
    async with httpx.AsyncClient() as client:
        r = await client.get(f"{API_BASE}/menu/{category_id}")
        items = r.json()
    lines = []
    for i in items:
        line = f"{i['name']} — {i['price']} ₽"
        if i.get("description"):
            line += f"\n{i['description']}"
        lines.append(line)
    buttons = [
        {"label": f"+ {i['name']}", "payload": {"intent": "add_item", "item_id": i["id"]}}
        for i in items
    ]
    cart = _carts.get(msg.user_id, {})
    if cart:
        total_qty = sum(v["qty"] for v in cart.values())
        buttons.append({"label": f"Корзина ({total_qty})", "payload": {"intent": "show_cart"}})
    buttons.append({"label": "← Категории", "payload": {"intent": "open_menu"}})
    return OutgoingMessage(
        user_id=msg.user_id,
        text="\n\n".join(lines) or "Категория пуста",
        buttons=buttons,
    )


async def _add_item(msg: IncomingMessage, item_id: int) -> OutgoingMessage:
    if not item_id:
        return OutgoingMessage(user_id=msg.user_id, text="Ошибка: позиция не указана.", buttons=_MAIN_BUTTONS)

    async with httpx.AsyncClient() as client:
        r = await client.get(f"{API_BASE}/item/{item_id}")
    if r.status_code != 200:
        return OutgoingMessage(user_id=msg.user_id, text="Позиция недоступна.", buttons=_MAIN_BUTTONS)

    item = r.json()
    cart = _carts.setdefault(msg.user_id, {})
    if item_id in cart:
        cart[item_id]["qty"] += 1
    else:
        cart[item_id] = {"name": item["name"], "price": Decimal(str(item["price"])), "qty": 1}

    qty = cart[item_id]["qty"]
    total_qty = sum(v["qty"] for v in cart.values())
    total = sum(v["price"] * v["qty"] for v in cart.values())

    text = (
        f"✓ {item['name']} добавлен в корзину"
        + (f" (×{qty})" if qty > 1 else "")
        + f"\n\nВ корзине: {total_qty} поз. на {total} ₽"
    )
    return OutgoingMessage(
        user_id=msg.user_id,
        text=text,
        buttons=[
            {"label": "Продолжить покупки", "payload": {"intent": "open_menu"}},
            {"label": f"Корзина ({total_qty})", "payload": {"intent": "show_cart"}},
        ],
    )


async def _show_cart(msg: IncomingMessage) -> OutgoingMessage:
    cart = _carts.get(msg.user_id, {})
    if not cart:
        return OutgoingMessage(
            user_id=msg.user_id,
            text="Корзина пуста.",
            buttons=[{"label": "Меню", "payload": {"intent": "open_menu"}}],
        )

    lines = []
    total = Decimal("0")
    for item_id, v in cart.items():
        subtotal = v["price"] * v["qty"]
        total += subtotal
        lines.append(f"{v['name']} × {v['qty']} = {subtotal} ₽")

    text = "Ваша корзина:\n" + "\n".join(lines) + f"\n\nИтого: {total} ₽"
    return OutgoingMessage(
        user_id=msg.user_id,
        text=text,
        buttons=[
            {"label": "Оформить заказ", "payload": {"intent": "confirm_order"}},
            {"label": "Очистить", "payload": {"intent": "clear_cart"}},
            {"label": "← Меню", "payload": {"intent": "open_menu"}},
        ],
    )


async def _confirm_order(msg: IncomingMessage) -> OutgoingMessage:
    cart = _carts.get(msg.user_id, {})
    if not cart:
        return OutgoingMessage(
            user_id=msg.user_id,
            text="Корзина пуста — нечего оформлять.",
            buttons=[{"label": "Меню", "payload": {"intent": "open_menu"}}],
        )

    async with httpx.AsyncClient() as client:
        ru = await client.get(f"{API_BASE}/user/{msg.user_id}")
        user = ru.json()
        r = await client.post(
            f"{API_BASE}/order/",
            json={
                "user_id": user["id"],
                "items": [{"item_id": iid, "qty": v["qty"]} for iid, v in cart.items()],
                "bonuses_to_spend": "0",
            },
        )

    if r.status_code != 200:
        return OutgoingMessage(
            user_id=msg.user_id,
            text=f"Ошибка оформления заказа: {r.text}",
            buttons=_MAIN_BUTTONS,
        )

    order = r.json()
    _carts.pop(msg.user_id, None)

    if settings.admin_max_user_id:
        await _notify_admin(order, user)

    return OutgoingMessage(
        user_id=msg.user_id,
        text=f"Заказ №{order['id']} принят!\nСумма: {order['total_amount']} ₽\n\nСпасибо, ждём вас!",
        buttons=_MAIN_BUTTONS,
    )


async def _notify_admin(order: dict, user: dict) -> None:
    items_text = "\n".join(
        f"  • {i['name']} × {i['qty']} — {i['price']} ₽"
        for i in order["items"]
    )
    phone = user.get("phone") or "не указан"
    text = (
        f"🛎 Новый заказ #{order['id']}\n"
        f"Клиент: {user['name']} ({phone})\n"
        f"Состав:\n{items_text}\n"
        f"Итого: {order['total_amount']} ₽"
    )
    async with httpx.AsyncClient() as client:
        await client.post(
            "https://botapi.max.ru/messages",
            params={"user_id": settings.admin_max_user_id},
            headers={"Authorization": settings.max_token},
            json={"text": text},
            timeout=10,
        )


async def _show_profile(msg: IncomingMessage) -> OutgoingMessage:
    async with httpx.AsyncClient() as client:
        r = await client.get(f"{API_BASE}/user/{msg.user_id}")
        u = r.json()
    text = f"Имя: {u['name']}\nТелефон: {u['phone'] or '—'}\nДата рождения: {u['birth_date'] or '—'}\nБонусы: {u['bonus_balance']} ₽"
    return OutgoingMessage(
        user_id=msg.user_id,
        text=text,
        buttons=[
            {"label": "Изменить имя", "payload": {"intent": "edit_name"}},
            {"label": "Изменить дату рождения", "payload": {"intent": "edit_birth_date"}},
            {"label": "← Главное меню", "payload": {"intent": "open_menu"}},
        ],
    )


async def _show_bonuses(msg: IncomingMessage) -> OutgoingMessage:
    async with httpx.AsyncClient() as client:
        ru = await client.get(f"{API_BASE}/user/{msg.user_id}")
        user = ru.json()
        rb = await client.get(f"{API_BASE}/bonuses/{user['id']}")
        data = rb.json()
    return OutgoingMessage(
        user_id=msg.user_id,
        text=f"Ваш бонусный баланс: {data['balance']} ₽",
        buttons=[{"label": "← Главное меню", "payload": {"intent": "open_menu"}}],
    )


async def _show_history(msg: IncomingMessage) -> OutgoingMessage:
    async with httpx.AsyncClient() as client:
        ru = await client.get(f"{API_BASE}/user/{msg.user_id}")
        user = ru.json()
        rh = await client.get(f"{API_BASE}/orders/{user['id']}")
        orders = rh.json()
    if not orders:
        return OutgoingMessage(
            user_id=msg.user_id,
            text="История заказов пуста.",
            buttons=[{"label": "← Главное меню", "payload": {"intent": "open_menu"}}],
        )
    blocks = []
    buttons = []
    for o in orders:
        item_lines = "\n".join(f"• {i['name']} × {i['qty']} — {i['price']} ₽" for i in o["items"])
        blocks.append(f"Заказ #{o['id']} от {o['created_at'][:10]} — {o['total_amount']} ₽\n{item_lines}")
        buttons.append(
            {"label": f"Повторить #{o['id']}", "payload": {"intent": "repeat_order", "order_id": o["id"]}}
        )
    buttons.append({"label": "← Главное меню", "payload": {"intent": "open_menu"}})
    return OutgoingMessage(user_id=msg.user_id, text="\n\n".join(blocks), buttons=buttons)


async def _repeat_order(msg: IncomingMessage, order_id: int) -> OutgoingMessage:
    async with httpx.AsyncClient() as client:
        ru = await client.get(f"{API_BASE}/user/{msg.user_id}")
        user = ru.json()
        r = await client.post(f"{API_BASE}/order/{order_id}/repeat", params={"user_id": user["id"]})
        data = r.json()
    text = f"Заказ повторён. Сумма: {data['order']['total_amount']} ₽"
    if data.get("unavailable_item_ids"):
        text += f"\nНедоступные позиции пропущены: {data['unavailable_item_ids']}"
    return OutgoingMessage(
        user_id=msg.user_id,
        text=text,
        buttons=[{"label": "← История заказов", "payload": {"intent": "show_order_history"}}],
    )
