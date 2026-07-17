"""add_news_table

Revision ID: 7f2a9c3d1b6e
Revises: 5a1f2b3c4d5e
Create Date: 2026-07-17 12:00:00.000000

"""
from typing import Sequence, Union
from datetime import datetime
from alembic import op
import sqlalchemy as sa

revision: str = '7f2a9c3d1b6e'
down_revision: Union[str, None] = '5a1f2b3c4d5e'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

news_table = sa.table(
    'news',
    sa.column('mid', sa.String),
    sa.column('tag', sa.String),
    sa.column('title', sa.String),
    sa.column('text', sa.Text),
    sa.column('image_path', sa.String),
    sa.column('published_at', sa.DateTime),
)

SEED = [
    dict(tag='Новинка', title='Пицца «Гриль» теперь в меню',
         text='Добавили новую пиццу с пепперони, шампиньонами, болгарским перцем и оливками на тонком хрустящем тесте. Обязательно попробуйте!',
         published_at=datetime(2025, 6, 25)),
    dict(tag='График работы', title='Открываемся по воскресеньям',
         text='Отличные новости! Теперь IrMa работает все семь дней в неделю. В выходные ждём вас с 10:00 до 20:00 — приходите с семьёй на вкусный завтрак.',
         published_at=datetime(2025, 6, 10)),
    dict(tag='Событие', title='IrMa — нам исполняется 3 года!',
         text='15 июля отмечаем день рождения кафе: скидки на всё меню, живая музыка с 18:00 и сладкие подарки первым 30 гостям. Не пропустите!',
         published_at=datetime(2025, 6, 1)),
    dict(tag='Новинка', title='Летние боулы с киноа и авокадо',
         text='Обновили летнее меню: три новых боула с киноа, авокадо, лососем и сезонными овощами. Лёгко, свежо и очень по-летнему.',
         published_at=datetime(2025, 5, 20)),
    dict(tag='Открытие', title='Открыли летнюю веранду',
         text='Теперь можно позавтракать и поужинать на свежем воздухе — веранда работает ежедневно до заката. Места лучше бронировать заранее.',
         published_at=datetime(2025, 5, 5)),
    dict(tag='Достижение', title='IrMa вошла в топ-10 кафе города',
         text='По версии городского гастрономического гида мы попали в десятку лучших семейных кафе. Спасибо, что выбираете нас!',
         published_at=datetime(2025, 4, 22)),
    dict(tag='Команда', title='У нас новый шеф-кондитер',
         text='К команде IrMa присоединилась шеф-кондитер с опытом работы в европейских кондитерских. Уже готовит новые десерты для меню.',
         published_at=datetime(2025, 4, 10)),
]


def upgrade() -> None:
    op.create_table(
        'news',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('mid', sa.String(), nullable=True),
        sa.Column('tag', sa.String(), nullable=False, server_default='Новости'),
        sa.Column('title', sa.String(), nullable=False),
        sa.Column('text', sa.Text(), nullable=False, server_default=''),
        sa.Column('image_path', sa.String(), nullable=True),
        sa.Column('published_at', sa.DateTime(), nullable=False),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now()),
    )
    op.create_unique_constraint('uq_news_mid', 'news', ['mid'])
    op.bulk_insert(news_table, SEED)


def downgrade() -> None:
    op.drop_table('news')
