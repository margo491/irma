"""Тесты бизнес-логики бонусов без обращения к БД."""
from decimal import Decimal
import pytest
from unittest.mock import AsyncMock, MagicMock


@pytest.mark.asyncio
async def test_earn_bonuses_5_percent():
    from app.services.bonus import earn_bonuses

    user = MagicMock(bonus_balance=Decimal("0"))
    order = MagicMock(id=1, total_amount=Decimal("1000"))
    db = AsyncMock()
    db.add = MagicMock()

    earned = await earn_bonuses(db, user, order)

    assert earned == Decimal("50.00")
    assert user.bonus_balance == Decimal("50.00")


@pytest.mark.asyncio
async def test_spend_bonuses_capped_at_20_percent():
    from app.services.bonus import spend_bonuses

    user = MagicMock(bonus_balance=Decimal("500"))
    order = MagicMock(id=1, total_amount=Decimal("1000"))
    db = AsyncMock()
    db.add = MagicMock()

    # Пытаемся списать 300, но лимит 20% = 200
    spent = await spend_bonuses(db, user, order, Decimal("300"))

    assert spent == Decimal("200.00")
    assert user.bonus_balance == Decimal("300.00")


@pytest.mark.asyncio
async def test_spend_bonuses_capped_at_balance():
    from app.services.bonus import spend_bonuses

    user = MagicMock(bonus_balance=Decimal("50"))
    order = MagicMock(id=1, total_amount=Decimal("1000"))
    db = AsyncMock()
    db.add = MagicMock()

    # Лимит 20% = 200, но на балансе только 50
    spent = await spend_bonuses(db, user, order, Decimal("200"))

    assert spent == Decimal("50.00")
    assert user.bonus_balance == Decimal("0.00")
