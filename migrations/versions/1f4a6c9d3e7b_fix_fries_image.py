"""fix_fries_image

Картофель фри в menu_items ссылался на /dishes/1.png — тот же файл, что и
Салат «Весенний», из-за чего у обоих блюд показывалась одна (причём чужая)
картинка. Даём картошке фри собственное фото (/dishes/28.png).

Revision ID: 1f4a6c9d3e7b
Revises: 6b3e9f1a7c2d
Create Date: 2026-08-13 00:00:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = '1f4a6c9d3e7b'
down_revision: Union[str, None] = '6b3e9f1a7c2d'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

items_table = sa.table(
    'menu_items',
    sa.column('name', sa.String),
    sa.column('image_url', sa.String),
)


def upgrade() -> None:
    op.execute(
        items_table.update()
        .where(items_table.c.name == 'Картофель фри 150 г')
        .values(image_url='/dishes/28.png')
    )


def downgrade() -> None:
    op.execute(
        items_table.update()
        .where(items_table.c.name == 'Картофель фри 150 г')
        .values(image_url='/dishes/1.png')
    )
