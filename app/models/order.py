from sqlalchemy import String, Numeric, DateTime, ForeignKey, JSON, func
from sqlalchemy.orm import Mapped, mapped_column
from decimal import Decimal
from datetime import datetime
from app.database import Base


class Order(Base):
    __tablename__ = "orders"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    items: Mapped[list] = mapped_column(JSON, nullable=False)  # [{item_id, qty, price}]
    total_amount: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    bonuses_used: Mapped[Decimal] = mapped_column(Numeric(10, 2), default=0)
    bonuses_earned: Mapped[Decimal] = mapped_column(Numeric(10, 2), default=0)
    status: Mapped[str] = mapped_column(String, default="created")  # created | completed | cancelled
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
