"""add TTSCache table

Revision ID: a1b2c3d4e5f6
Revises: e3e4f3e26ee1
Create Date: 2025-11-02 00:00:00

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'a1b2c3d4e5f6'
down_revision = 'e3e4f3e26ee1'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        'ttscache',
        sa.Column('cache_id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('news_id', sa.String(length=255), nullable=False, index=True),
        sa.Column('headline_hash', sa.String(length=64), nullable=False, index=True),
        sa.Column('storage', sa.String(length=20), nullable=False),
        sa.Column('key_or_path', sa.Text(), nullable=False),
        sa.Column('url', sa.Text(), nullable=True),
        sa.Column('size_bytes', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('last_accessed_at', sa.DateTime(), nullable=True),
    )
    op.create_index('ix_ttscache_news_id', 'ttscache', ['news_id'])
    op.create_index('ix_ttscache_headline_hash', 'ttscache', ['headline_hash'])


def downgrade() -> None:
    op.drop_index('ix_ttscache_headline_hash', table_name='ttscache')
    op.drop_index('ix_ttscache_news_id', table_name='ttscache')
    op.drop_table('ttscache')
