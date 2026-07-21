"""resync_real_menu

Заменяет тестовые заглушки в menu_categories/menu_items на настоящее меню
сайта (landing/menu.html — 5 категорий, 31 блюдо) вместе с реальными фото
из landing/dishes и landing/menu/pizza. Нужно было для корректного экспорта
в ChatMarket (там обязательна картинка у каждого товара) и чтобы бот
показывал то же меню, что и сайт.

Revision ID: 6b3e9f1a7c2d
Revises: 2d5c8b1e4a7f
Create Date: 2026-07-21 10:00:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = '6b3e9f1a7c2d'
down_revision: Union[str, None] = '2d5c8b1e4a7f'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

categories_table = sa.table(
    'menu_categories',
    sa.column('id', sa.Integer),
    sa.column('name', sa.String),
    sa.column('sort_order', sa.Integer),
)

items_table = sa.table(
    'menu_items',
    sa.column('category_id', sa.Integer),
    sa.column('name', sa.String),
    sa.column('description', sa.String),
    sa.column('price', sa.Numeric),
    sa.column('image_url', sa.String),
    sa.column('is_available', sa.Boolean),
)

CATEGORIES = [
    dict(id=1, name='Салаты', sort_order=1),
    dict(id=2, name='Кофе и чай', sort_order=2),
    dict(id=3, name='Блины и бургеры', sort_order=3),
    dict(id=4, name='Пицца', sort_order=4),
    dict(id=5, name='Холодные напитки', sort_order=5),
]

ITEMS = [
    # Салаты
    dict(category_id=1, name='Салат «Весенний»', price=280, image_url='/dishes/1.png',
         description='Помидоры черри, оливки, авокадо, базилик, кукуруза, кешью, оливковое масло'),
    dict(category_id=1, name='Салат «Свежесть»', price=220, image_url='/dishes/2.png',
         description='Редис, огурец, помидоры черри, листья салата, руккола, укроп'),
    dict(category_id=1, name='Салат «Греческий»', price=310, image_url='/dishes/3.png',
         description='Огурцы, помидоры черри, сыр фета, оливки, красный лук, укроп'),
    dict(category_id=1, name='Салат «Мексикано»', price=350, image_url='/dishes/4.png',
         description='Куриное филе, кукуруза, чёрная фасоль, авокадо, красный лук, помидоры'),
    dict(category_id=1, name='Салат «Блю»', price=380, image_url='/dishes/5.png',
         description='Руккола, болгарский перец, помидоры черри, сыр с голубой плесенью'),
    dict(category_id=1, name='Салат «Цезарь»', price=320, image_url='/dishes/6.png',
         description='Куриное филе, листья романо, гренки, соус Цезарь, пармезан'),
    dict(category_id=1, name='Салат «Деревенский»', price=290, image_url='/dishes/7.png',
         description='Куриная грудка, помидоры черри, огурцы, сыр фета, гренки, айсберг'),

    # Кофе и чай
    dict(category_id=2, name='Американо', price=120, image_url='/dishes/8.png',
         description='Двойной эспрессо, горячая вода, зёрна Arabica'),
    dict(category_id=2, name='Чёрный кофе', price=90, image_url='/dishes/9.png',
         description='Молотый кофе, горячая вода'),
    dict(category_id=2, name='Латте', price=180, image_url='/dishes/10.png',
         description='Двойной эспрессо, взбитое молоко'),
    dict(category_id=2, name='Чай чёрный', price=100, image_url='/dishes/11.png',
         description='Цейлонский чай, листья мяты'),
    dict(category_id=2, name='Чай фруктовый', price=150, image_url='/dishes/12.png',
         description='Облепиха, шиповник, цитрус, мёд'),
    dict(category_id=2, name='Капучино карамельный', price=210, image_url='/dishes/13.png',
         description='Эспрессо, молоко, карамельный сироп, взбитые сливки'),

    # Блины и бургеры
    dict(category_id=3, name='Блин «Жюльен»', price=470, image_url='/dishes/14.png',
         description='Блин, курица, сливочный соус, пармезан, моцарелла, шампиньоны, лук фри, сырный соус, соус терияки'),
    dict(category_id=3, name='Блин с форелью', price=480, image_url='/dishes/15.png',
         description='Блин, форель, салат, моцарелла, творожный сыр, огурец, черри'),
    dict(category_id=3, name='Блин с ветчиной', price=430, image_url='/dishes/16.png',
         description='Блин, ветчина, салат, моцарелла, творожный сыр, огурец, черри'),
    dict(category_id=3, name='Блин с бананом и нутеллой', price=430, image_url='/dishes/17.png',
         description='Блин, банан, нутелла'),
    dict(category_id=3, name='Бургер с говядиной', price=520, image_url='/dishes/18.png',
         description='Булочка бриошь, соус томатный, соус барбекю, котлета из говядины, помидор, солёный огурец, салат, сыр, лук репчатый'),
    dict(category_id=3, name='Наггетсы 6 шт', price=340, image_url='/dishes/19.png',
         description='Подаются с сырным соусом и кетчупом'),
    dict(category_id=3, name='Картофель фри 150 г', price=240, image_url='/dishes/1.png',
         description='Подаётся с сырным соусом и кетчупом'),

    # Пицца
    dict(category_id=4, name='Пицца «Креветка/Лосось»', price=950, image_url='/menu/pizza/losos-krevetka.png',
         description='Лосось, креветка, сливочная основа, пармезан, черри, моцарелла, творожный сыр, соус терияки, руккола (30 см, 600 г)'),
    dict(category_id=4, name='Пицца «Ветчина/Бекон»', price=750, image_url='/menu/pizza/vetchina-bekon.png',
         description='Томатный соус, ветчина, моцарелла, помидор, солёные огурчики, бекон, руккола (30 см, 600 г)'),
    dict(category_id=4, name='Пицца «Курица/Грибы»', price=750, image_url='/menu/pizza/kuritsa-griby.jpg',
         description='Курица, шампиньоны, сливочная основа, пармезан, моцарелла, соус терияки, лук фри (30 см, 550 г)'),
    dict(category_id=4, name='Пицца «4 сыра»', price=750, image_url='/menu/pizza/4-syra.jpg',
         description='Моцарелла, горгонзола, пармезан, грюйер, соус альфредо (30 см, 550 г)'),
    dict(category_id=4, name='Пицца «Мясная»', price=780, image_url='/menu/pizza/myasnaya.jpg',
         description='Пепперони, курица, бекон, томатная основа, моцарелла, томаты, сырный соус (30 см, 550 г)'),
    dict(category_id=4, name='Пицца «Пепперони»', price=690, image_url='/menu/pizza/pepperoni.jpg',
         description='Соус томатный, моцарелла, пепперони (30 см, 550 г)'),
    dict(category_id=4, name='Пицца «Курица/Ветчина/Ананас»', price=750, image_url='/menu/pizza/kuritsa-vetchina-ananas.jpg',
         description='Курица, ананас, ветчина, сливочная основа, пармезан, моцарелла, соус свит чили (30 см, 550 г)'),

    # Холодные напитки
    dict(category_id=5, name='Кола со льдом', price=120, image_url='/dishes/24.png',
         description='Газированный напиток, лёд'),
    dict(category_id=5, name='Клубничный лимонад', price=180, image_url='/dishes/25.png',
         description='Клубника, газированная вода, мята, лёд'),
    dict(category_id=5, name='Голубой лимонад', price=200, image_url='/dishes/26.png',
         description='Синий кюрасао, лайм, мята, газированная вода, лёд'),
    dict(category_id=5, name='Лимонад с лимоном', price=150, image_url='/dishes/27.png',
         description='Лимон, газированная вода, лёд'),
]

for item in ITEMS:
    item['is_available'] = True


def upgrade() -> None:
    op.execute('DELETE FROM menu_items')
    op.execute('DELETE FROM menu_categories')
    op.bulk_insert(categories_table, CATEGORIES)
    op.bulk_insert(items_table, ITEMS)


def downgrade() -> None:
    op.execute('DELETE FROM menu_items')
    op.execute('DELETE FROM menu_categories')
