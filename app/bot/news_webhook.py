"""Вебхук бота-читателя новостного канала — авто-публикация постов канала в «Новости» на сайте."""
import logging
import re
from datetime import datetime
from pathlib import Path

import httpx
from fastapi import APIRouter, Request
from sqlalchemy import select

from app.database import async_session
from app.models.news import News

log = logging.getLogger(__name__)
router = APIRouter()

NEWS_CHAT_ID = -71665082178843
UPLOAD_DIR = Path("uploads/news")

_recent: list[dict] = []
_MAX_KEEP = 20


@router.post("/webhook/news")
async def news_webhook(request: Request):
    payload = await request.json()

    _recent.append(payload)
    if len(_recent) > _MAX_KEEP:
        del _recent[0]

    try:
        await _handle_event(payload)
    except Exception:
        log.exception("Failed to process news webhook event")

    return {"ok": True}


@router.get("/webhook/news/debug")
async def news_webhook_debug():
    return {"count": len(_recent), "events": _recent}


async def _handle_event(payload: dict) -> None:
    if payload.get("update_type") != "message_created":
        return

    message = payload.get("message") or {}
    recipient = message.get("recipient") or {}
    if recipient.get("chat_id") != NEWS_CHAT_ID:
        return

    body = message.get("body") or {}
    mid = body.get("mid")
    if not mid:
        return

    attachments = body.get("attachments") or []

    async with async_session() as session:
        existing = await session.scalar(select(News).where(News.mid == mid))
        if existing:
            # Retry filling in a video we may have missed the first time
            # (e.g. an earlier deploy that didn't download it yet).
            if not existing.video_path:
                video_path = await _download_first_video(attachments, mid)
                if video_path:
                    existing.video_path = video_path
                    await session.commit()
            return

        text = (body.get("text") or "").strip()
        lines = [line.strip() for line in text.splitlines() if line.strip()]
        title = lines[0][:120] if lines else "Новый пост"
        rest = "\n".join(lines[1:]).strip()
        if not rest:
            rest = text

        image_path = await _download_first_image(attachments, mid)
        video_path = await _download_first_video(attachments, mid)

        timestamp_ms = message.get("timestamp")
        published_at = (
            datetime.fromtimestamp(timestamp_ms / 1000) if timestamp_ms else datetime.utcnow()
        )

        session.add(
            News(
                mid=mid,
                tag="Новости",
                title=title,
                text=rest,
                image_path=image_path,
                video_path=video_path,
                published_at=published_at,
            )
        )
        await session.commit()


async def _download_first_image(attachments: list[dict], mid: str) -> str | None:
    url = None
    for att in attachments:
        if att.get("type") == "image":
            url = (att.get("payload") or {}).get("url")
            if url:
                break
    if not url:
        for att in attachments:
            thumb_url = (att.get("thumbnail") or {}).get("url")
            if thumb_url:
                url = thumb_url
                break
    if not url:
        return None

    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    safe_mid = re.sub(r"[^a-zA-Z0-9_.-]", "_", mid)

    async with httpx.AsyncClient() as client:
        resp = await client.get(url, timeout=20, headers={"User-Agent": "Mozilla/5.0"})
        resp.raise_for_status()

    content_type = resp.headers.get("content-type", "")
    ext = "jpg"
    if "png" in content_type:
        ext = "png"
    elif "webp" in content_type:
        ext = "webp"
    elif "jpeg" in content_type:
        ext = "jpg"

    filename = f"{safe_mid}.{ext}"
    (UPLOAD_DIR / filename).write_bytes(resp.content)

    return f"/uploads/news/{filename}"


async def _download_first_video(attachments: list[dict], mid: str) -> str | None:
    url = None
    for att in attachments:
        if att.get("type") == "video":
            url = (att.get("payload") or {}).get("url")
            if url:
                break
    if not url:
        return None

    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    safe_mid = re.sub(r"[^a-zA-Z0-9_.-]", "_", mid)

    async with httpx.AsyncClient() as client:
        resp = await client.get(url, timeout=60, headers={"User-Agent": "Mozilla/5.0"})
        resp.raise_for_status()

    filename = f"{safe_mid}.mp4"
    (UPLOAD_DIR / filename).write_bytes(resp.content)

    return f"/uploads/news/{filename}"
