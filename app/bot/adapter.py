from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass
class IncomingMessage:
    user_id: str      # external_id отправителя (для БД и сессий)
    chat_id: str      # id чата (для отправки ответа)
    channel: str      # "max" | "telegram" | ...
    text: str
    payload: dict     # данные кнопок / callback


@dataclass
class OutgoingMessage:
    user_id: str
    text: str
    buttons: list[dict] | None = None  # [{label, payload}]
    image_url: str | None = None


class BotAdapter(ABC):
    """Транспортный слой. Реализуется отдельно для каждого канала."""

    @abstractmethod
    async def send(self, message: OutgoingMessage) -> None: ...

    @abstractmethod
    async def parse(self, raw: dict) -> IncomingMessage: ...
