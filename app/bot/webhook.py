from fastapi import APIRouter, Request

from app.bot.handlers import handle
from app.bot.intents import detect_intent
from app.bot.max_adapter import MaxAdapter
from app.config import settings

router = APIRouter()
_adapter = MaxAdapter(token=settings.max_token)


@router.post("/webhook")
async def webhook(request: Request):
    payload = await request.json()

    msg = await _adapter.parse(payload)
    if not msg.user_id:
        return {"ok": True}

    intent, extra = detect_intent(msg)
    reply = await handle(intent, msg, extra)
    await _adapter.send(reply)

    return {"ok": True}
