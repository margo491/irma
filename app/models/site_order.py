from decimal import Decimal
from datetime import datetime
from sqlalchemy import String, Numeric, DateTime, JSON, func
from sqlalchemy.orm import Mapped, mapped_column
from app.database import Base


class SiteOrder(Base):
    __tablename__ = "site_orders"

    id: Mapped[int] = mapped_column(primary_key=True)
    phone: Mapped[str] = mapped_column(String, nullable=False)
    items: Mapped[list] = mapped_column(JSON, nullable=False)  # [{name, price, qty}]
    total_amount: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    status: Mapped[str] = mapped_column(String, default="new")  # new | processing | done
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
