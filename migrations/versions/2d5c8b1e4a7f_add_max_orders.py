"""add_max_orders

Revision ID: 2d5c8b1e4a7f
Revises: 7e1f6a3b8d2c
Create Date: 2026-07-20 15:00:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = '2d5c8b1e4a7f'
down_revision: Union[str, None] = '7e1f6a3b8d2c'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'max_orders',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('phone', sa.String(), nullable=True),
        sa.Column('description', sa.Text(), nullable=False),
        sa.Column('total_amount', sa.Numeric(10, 2), nullable=False),
        sa.Column('status', sa.String(), nullable=False, server_default='new'),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now()),
    )


def downgrade() -> None:
    op.drop_table('max_orders')
