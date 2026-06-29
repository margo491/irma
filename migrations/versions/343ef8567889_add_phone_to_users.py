"""add_phone_to_users

Revision ID: 343ef8567889
Revises: 20c7a16e999d
Create Date: 2026-06-29 13:41:30.979765

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = '343ef8567889'
down_revision: Union[str, None] = '20c7a16e999d'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('users', sa.Column('phone', sa.String(), nullable=True))


def downgrade() -> None:
    op.drop_column('users', 'phone')
