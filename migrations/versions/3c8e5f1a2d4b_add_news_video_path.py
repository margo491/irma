"""add_news_video_path

Revision ID: 3c8e5f1a2d4b
Revises: 7f2a9c3d1b6e
Create Date: 2026-07-18 14:00:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = '3c8e5f1a2d4b'
down_revision: Union[str, None] = '7f2a9c3d1b6e'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('news', sa.Column('video_path', sa.String(), nullable=True))


def downgrade() -> None:
    op.drop_column('news', 'video_path')
