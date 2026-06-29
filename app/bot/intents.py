from enum import Enum

from app.bot.adapter import IncomingMessage


class Intent(str, Enum):
    OPEN_MENU = "open_menu"
    OPEN_CATEGORY = "open_category"
    ADD_ITEM = "add_item"
    SHOW_CART = "show_cart"
    CLEAR_CART = "clear_cart"
    CONFIRM_ORDER = "confirm_order"
    SHOW_PROFILE = "show_profile"
    SHOW_BONUSES = "show_bonuses"
    SHOW_ORDER_HISTORY = "show_order_history"
    REPEAT_ORDER = "repeat_order"
    UNKNOWN = "unknown"


_TEXT_MAP: dict[str, Intent] = {
    "меню": Intent.OPEN_MENU,
    "menu": Intent.OPEN_MENU,
    "профиль": Intent.SHOW_PROFILE,
    "profile": Intent.SHOW_PROFILE,
    "бонусы": Intent.SHOW_BONUSES,
    "bonuses": Intent.SHOW_BONUSES,
    "история": Intent.SHOW_ORDER_HISTORY,
    "history": Intent.SHOW_ORDER_HISTORY,
    "привет": Intent.OPEN_MENU,
    "start": Intent.OPEN_MENU,
    "/start": Intent.OPEN_MENU,
}


def detect_intent(msg: IncomingMessage) -> tuple[Intent, dict]:
    """Возвращает (Intent, extra_payload) из входящего сообщения."""
    if msg.payload:
        raw_intent = msg.payload.get("intent", "")
        try:
            intent = Intent(raw_intent)
        except ValueError:
            intent = Intent.UNKNOWN
        return intent, msg.payload

    key = msg.text.strip().lower()
    intent = _TEXT_MAP.get(key, Intent.UNKNOWN)
    return intent, {}
