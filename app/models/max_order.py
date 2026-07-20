from decimal import Decimal
from datetime import datetime
from sqlalchemy import String, Text, Numeric, DateTime, func
from sqlalchemy.orm import Mapped, mapped_column
from app.database import Base


class MaxOrder(Base):
    """Заказ из магазина ChatMarket в MAX — вносится вручную персоналом,
    т.к. ChatMarket уведомляет о заказах в Telegram/почту, а не по API."""

    __tablename__ = "max_orders"

    id: Mapped[int] = mapped_column(primary_key=True)
    phone: Mapped[str | None] = mapped_column(String, nullable=True)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    total_amount: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    status: Mapped[str] = mapped_column(String, default="new")  # new | confirmed | done | cancelled
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
