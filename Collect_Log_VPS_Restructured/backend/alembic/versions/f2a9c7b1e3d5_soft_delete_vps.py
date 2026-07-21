"""soft delete VPS (deleted_at + unicite partielle du nom)

Revision ID: f2a9c7b1e3d5
Revises: 3aebcac69df5
Create Date: 2026-07-21 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers
revision = 'f2a9c7b1e3d5'
down_revision = '3aebcac69df5'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Suppression logique : une date non nulle marque un VPS supprimé.
    op.add_column(
        'vps_servers',
        sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
    )

    # L'unicité globale du nom empêcherait de réutiliser le nom d'un VPS
    # supprimé (la ligne reste en base). On la remplace par une unicité
    # PARTIELLE : le nom n'est unique que parmi les VPS actifs.
    op.drop_constraint('vps_servers_name_key', 'vps_servers', type_='unique')
    op.create_index(
        'uq_vps_servers_name_active',
        'vps_servers',
        ['name'],
        unique=True,
        postgresql_where=sa.text('deleted_at IS NULL'),
    )


def downgrade() -> None:
    op.drop_index('uq_vps_servers_name_active', table_name='vps_servers')
    op.create_unique_constraint('vps_servers_name_key', 'vps_servers', ['name'])
    op.drop_column('vps_servers', 'deleted_at')
