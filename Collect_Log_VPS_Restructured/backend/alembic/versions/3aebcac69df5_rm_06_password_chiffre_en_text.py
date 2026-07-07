"""RM-06 password chiffre en TEXT

Revision ID: 3aebcac69df5
Revises: 7fd3b5d36be0
Create Date: 2026-07-07 15:06:28.997442

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers
revision = '3aebcac69df5'
down_revision = '7fd3b5d36be0'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # password est chiffré au repos (EncryptedText, RM-06) : la colonne réelle
    # passe en TEXT car les jetons Fernet dépassent 500 caractères.
    op.alter_column('vps_servers', 'password',
               existing_type=sa.VARCHAR(length=500),
               type_=sa.Text(),
               existing_nullable=True)


def downgrade() -> None:
    op.alter_column('vps_servers', 'password',
               existing_type=sa.Text(),
               type_=sa.VARCHAR(length=500),
               existing_nullable=True)
