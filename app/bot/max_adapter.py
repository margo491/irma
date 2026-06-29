"""Адаптер для Max Bot API (botapi.max.ru)."""
import json
import math

import httpx

from app.bot.adapter import BotAdapter, IncomingMessage, OutgoingMessage

_BASE = "https://botapi.max.ru"
_ROW_SIZE = 2  # кнопок в ряду


class MaxAdapter(BotAdapter):
    def __init__(self, token: str) -> None:
        self._token = token

    # ------------------------------------------------------------------
    async def parse(self, raw: dict) -> IncomingMessage:
        update_type = raw.get("update_type", "")

        if update_type == "message_callback":
            cb = raw["callback"]
            user_id = str(cb["user"]["user_id"])
            chat_id = str(cb.get("chat_id") or cb["user"]["user_id"])
            try:
                payload = json.loads(cb.get("payload") or "{}")
            except (ValueError, TypeError):
                payload = {}
            return IncomingMessage(
                user_id=user_id,
                chat_id=chat_id,
                channel="max",
                text=payload.get("intent", ""),
                payload=payload,
            )

        # message_created или bot_started
        msg = raw.get("message", {})
        sender = msg.get("sender", {})
        user_id = str(sender.get("user_id", ""))
        chat_id = str(msg.get("recipient", {}).get("chat_id") or user_id)
        text = (msg.get("body") or {}).get("text", "") or ""
        return IncomingMessage(user_id=user_id, chat_id=chat_id, channel="max", text=text, payload={})

    # ------------------------------------------------------------------
    async def send(self, message: OutgoingMessage) -> None:
        body: dict = {
            "recipient": {"chat_id": int(message.user_id)},
            "body": {"text": message.text},
        }

        if message.buttons:
            rows = _split_rows(message.buttons, _ROW_SIZE)
            body["body"]["attachments"] = [
                {
                    "type": "inline_keyboard",
                    "payload": {
                        "buttons": [
                            [
                                {
                                    "type": "callback",
                                    "text": btn["label"],
                                    "payload": json.dumps(btn["payload"], ensure_ascii=False),
                                }
                                for btn in row
                            ]
                            for row in rows
                        ]
                    },
                }
            ]

        async with httpx.AsyncClient() as client:
            await client.post(
                f"{_BASE}/messages",
                headers={"Authorization": self._token},
                json=body,
                timeout=10,
            )


def _split_rows(buttons: list[dict], size: int) -> list[list[dict]]:
    n = math.ceil(len(buttons) / size)
    return [buttons[i * size : (i + 1) * size] for i in range(n)]
