"""add_site_orders_and_promos

Revision ID: 7e1f6a3b8d2c
Revises: 4b7d2f9a1c3e
Create Date: 2026-07-20 12:00:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = '7e1f6a3b8d2c'
down_revision: Union[str, None] = '4b7d2f9a1c3e'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

promos_table = sa.table(
    'promos',
    sa.column('icon', sa.String),
    sa.column('badge', sa.String),
    sa.column('title', sa.String),
    sa.column('text', sa.Text),
)

PROMO_SEED = [
    dict(icon='☀️', badge='Каждый день', title='Завтрак в подарок',
         text='При заказе от 600 ₽ с 9:00 до 12:00 — чашка кофе или чай в подарок. Идеально начать день вкусно.'),
    dict(icon='☕', badge='По вторникам', title='Два кофе по цене одного',
         text='Каждый вторник — любые два кофейных напитка за цену одного. Приходите вдвоём и пробуйте новинки вместе.'),
    dict(icon='🎁', badge='Постоянно', title='Бонусная программа',
         text='10% от каждого заказа через бота IrMa возвращается бонусами. Копите и тратьте на любимые блюда.'),
    dict(icon='🕕', badge='Будни, 15:00–17:00', title='Счастливые часы',
         text='Скидка 20% на всю выпечку и десерты каждый будний день с 15:00 до 17:00. Успейте порадовать себя сладким.'),
    dict(icon='🎈', badge='В день рождения', title='Десерт в подарок',
         text='Покажите документ в свой день рождения — любой десерт из витрины дарим бесплатно. Приходите отмечать с нами!'),
    dict(icon='👯', badge='Приведи друга', title='Скидка 15% на двоих',
         text='Приведите друга, который у нас впервые — получите скидку 15% на весь заказ для вас обоих.'),
    dict(icon='🍽️', badge='Будни, 12:00–16:00', title='Бизнес-ланч за 390 ₽',
         text='Суп, горячее и напиток на выбор — сытный обед по фиксированной цене каждый будний день.'),
]


def upgrade() -> None:
    op.create_table(
        'site_orders',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('phone', sa.String(), nullable=False),
        sa.Column('items', sa.JSON(), nullable=False),
        sa.Column('total_amount', sa.Numeric(10, 2), nullable=False),
        sa.Column('status', sa.String(), nullable=False, server_default='new'),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now()),
    )

    op.create_table(
        'promos',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('icon', sa.String(), nullable=False, server_default='🎁'),
        sa.Column('badge', sa.String(), nullable=False, server_default=''),
        sa.Column('title', sa.String(), nullable=False),
        sa.Column('text', sa.Text(), nullable=False, server_default=''),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now()),
    )
    op.bulk_insert(promos_table, PROMO_SEED)


def downgrade() -> None:
    op.drop_table('promos')
    op.drop_table('site_orders')
