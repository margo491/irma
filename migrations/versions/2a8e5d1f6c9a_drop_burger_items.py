"""drop_burger_items

Убирает «Бургер с говядиной», «Наггетсы 6 шт» и «Картофель фри 150 г» из
menu_items — позиции сняты с продажи на сайте. Заодно переименовывает
категорию 3 из «Блины и бургеры» в «Блины», так как бургеров в ней больше
не осталось.

Revision ID: 2a8e5d1f6c9a
Revises: 1f4a6c9d3e7b
Create Date: 2026-08-13 01:00:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = '2a8e5d1f6c9a'
down_revision: Union[str, None] = '1f4a6c9d3e7b'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

items_table = sa.table(
    'menu_items',
    sa.column('name', sa.String),
    sa.column('category_id', sa.Integer),
    sa.column('description', sa.String),
    sa.column('price', sa.Numeric),
    sa.column('image_url', sa.String),
    sa.column('is_available', sa.Boolean),
)

categories_table = sa.table(
    'menu_categories',
    sa.column('id', sa.Integer),
    sa.column('name', sa.String),
)

DROPPED = [
    dict(category_id=3, name='Бургер с говядиной',
         description='Булочка бриошь, соус томатный, соус барбекю, котлета из говядины, помидор, солёный огурец, салат, сыр, лук репчатый',
         price=520, image_url='/dishes/18.png'),
    dict(category_id=3, name='Наггетсы 6 шт',
         description='Подаются с сырным соусом и кетчупом',
         price=340, image_url='/dishes/19.png'),
    dict(category_id=3, name='Картофель фри 150 г',
         description='Подаётся с сырным соусом и кетчупом',
         price=240, image_url='/dishes/28.png'),
]

DROPPED_NAMES = [d['name'] for d in DROPPED]


def upgrade() -> None:
    op.execute(
        items_table.delete().where(items_table.c.name.in_(DROPPED_NAMES))
    )
    op.execute(
        categories_table.update()
        .where(categories_table.c.id == 3)
        .values(name='Блины')
    )


def downgrade() -> None:
    op.execute(
        categories_table.update()
        .where(categories_table.c.id == 3)
        .values(name='Блины и бургеры')
    )
    op.execute(
        items_table.insert().values(
            [{**d, 'is_available': True} for d in DROPPED]
        )
    )
