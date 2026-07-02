"""add users table for real authentication

Revision ID: 0002_users_auth
Revises: 
Create Date: 2026-06-15
"""
from alembic import op
import sqlalchemy as sa

revision = '0002_users_auth'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        'users',
        sa.Column('id',              sa.Integer(),     primary_key=True, autoincrement=True),
        sa.Column('username',        sa.String(100),   nullable=False,   unique=True, index=True),
        sa.Column('hashed_password', sa.String(500),   nullable=False),
        sa.Column('full_name',       sa.String(200),   nullable=True),
        sa.Column('role',            sa.String(50),    nullable=False,   server_default='viewer'),
        sa.Column('is_active',       sa.Integer(),     nullable=False,   server_default='1'),
        sa.Column('created_at',      sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('last_login',      sa.DateTime(timezone=True), nullable=True),
    )


def downgrade() -> None:
    op.drop_table('users')
