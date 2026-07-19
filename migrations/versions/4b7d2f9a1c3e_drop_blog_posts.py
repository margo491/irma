"""drop_blog_posts

Revision ID: 4b7d2f9a1c3e
Revises: 9a1d4e7c2f5b
Create Date: 2026-07-20 09:00:00.000000

"""
from typing import Sequence, Union
from datetime import datetime
from alembic import op
import sqlalchemy as sa

revision: str = '4b7d2f9a1c3e'
down_revision: Union[str, None] = '9a1d4e7c2f5b'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

blog_posts_table = sa.table(
    'blog_posts',
    sa.column('tag', sa.String),
    sa.column('title', sa.String),
    sa.column('excerpt', sa.Text),
    sa.column('text', sa.Text),
    sa.column('published_at', sa.DateTime),
)

# Kept only so `downgrade()` can restore the original seed if the blog
# feature is ever reinstated — the site never had real user-authored posts.
BLOG_SEED = [
    dict(tag='Напитки', title='5 рецептов идеального кофе для дома',
         excerpt='Раскрываем секреты, которые превратят обычное утро в маленькое удовольствие — без кофемашины за 100 тысяч.',
         text='Раскрываем секреты, которые превратят обычное утро в маленькое удовольствие — без кофемашины за 100 тысяч.',
         published_at=datetime(2025, 6, 5)),
    dict(tag='Советы', title='Как выбрать авокадо и не ошибиться',
         excerpt='Недозрелый или перезрелый — авокадо легко испортит блюдо. Рассказываем, как выбрать идеальный плод за 30 секунд.',
         text='Недозрелый или перезрелый — авокадо легко испортит блюдо. Рассказываем, как выбрать идеальный плод за 30 секунд.',
         published_at=datetime(2025, 5, 18)),
    dict(tag='Рецепт', title='Домашняя пицца: тонкое тесто без дрожжей',
         excerpt='Быстрый рецепт пиццы, которую можно приготовить за 40 минут — хрустящее тесто, томатный соус и любая начинка.',
         text='Быстрый рецепт пиццы, которую можно приготовить за 40 минут — хрустящее тесто, томатный соус и любая начинка.',
         published_at=datetime(2025, 5, 2)),
    dict(tag='О нас', title='История IrMa: как семейная кухня стала кафе',
         excerpt='Три года назад Ирина Маринич решила открыть маленькое место, где можно поесть как дома. Читайте, как всё начиналось.',
         text='Три года назад Ирина Маринич решила открыть маленькое место, где можно поесть как дома. Читайте, как всё начиналось.',
         published_at=datetime(2025, 4, 15)),
    dict(tag='Сезон', title='Летнее меню: что попробовать этим летом',
         excerpt='Клубничный лимонад, лёгкие салаты и холодный капучино — собрали всё самое освежающее из нашего летнего меню.',
         text='Клубничный лимонад, лёгкие салаты и холодный капучино — собрали всё самое освежающее из нашего летнего меню.',
         published_at=datetime(2025, 6, 1)),
    dict(tag='Рецепт', title='Тонкие блины: 3 теста для любого случая',
         excerpt='На кефире, на молоке и на воде — у каждого теста свой характер. Разбираемся, когда и какой выбрать.',
         text='На кефире, на молоке и на воде — у каждого теста свой характер. Разбираемся, когда и какой выбрать.',
         published_at=datetime(2025, 3, 10)),
]


def upgrade() -> None:
    op.drop_table('blog_posts')


def downgrade() -> None:
    op.create_table(
        'blog_posts',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('tag', sa.String(), nullable=False, server_default='Блог'),
        sa.Column('title', sa.String(), nullable=False),
        sa.Column('excerpt', sa.Text(), nullable=False, server_default=''),
        sa.Column('text', sa.Text(), nullable=False, server_default=''),
        sa.Column('image_path', sa.String(), nullable=True),
        sa.Column('published_at', sa.DateTime(), nullable=False),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now()),
    )
    op.bulk_insert(blog_posts_table, BLOG_SEED)
