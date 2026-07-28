"""cache d'enrichissement des IP (géoloc + réputation) — RM-34

Revision ID: d4f1a2b3c6e7
Revises: c3e8d1a4f6b2
Create Date: 2026-07-21 00:30:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers
revision = 'd4f1a2b3c6e7'
down_revision = 'c3e8d1a4f6b2'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        'ip_enrichment',
        sa.Column('ip', sa.String(length=45), primary_key=True),
        sa.Column('is_private', sa.Boolean(), nullable=True),
        sa.Column('country_code', sa.String(length=2), nullable=True),
        sa.Column('country', sa.String(length=100), nullable=True),
        sa.Column('city', sa.String(length=100), nullable=True),
        sa.Column('isp', sa.String(length=200), nullable=True),
        sa.Column('abuse_score', sa.Integer(), nullable=True),
        sa.Column('is_malicious', sa.Boolean(), nullable=True),
        sa.Column('providers', sa.String(length=100), nullable=True),
        sa.Column('fetched_at', sa.DateTime(timezone=True), server_default=sa.text('now()')),
    )


def downgrade() -> None:
    op.drop_table('ip_enrichment')
