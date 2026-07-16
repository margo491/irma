"""Временный диагностический вебхук для бота-читателя новостного канала.

Пока просто копит последние полученные события в памяти, чтобы понять
формат данных, которые прилетают от бота-подписчика канала в MAX.
"""
from fastapi import APIRouter, Request

router = APIRouter()

_recent: list[dict] = []
_MAX_KEEP = 20


@router.post("/webhook/news")
async def news_webhook(request: Request):
    payload = await request.json()
    _recent.append(payload)
    if len(_recent) > _MAX_KEEP:
        del _recent[0]
    return {"ok": True}


@router.get("/webhook/news/debug")
async def news_webhook_debug():
    return {"count": len(_recent), "events": _recent}
