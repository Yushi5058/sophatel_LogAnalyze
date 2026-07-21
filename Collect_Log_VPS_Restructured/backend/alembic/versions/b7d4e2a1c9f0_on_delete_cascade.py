"""ON DELETE CASCADE sur les FK vers log_collections / vps_servers

Revision ID: b7d4e2a1c9f0
Revises: f2a9c7b1e3d5
Create Date: 2026-07-21 00:10:00.000000

Une vraie suppression d'une collection (purge / rétention) supprime désormais
automatiquement ses log_entries, log_summaries et endpoint_stats. Idem : une
vraie suppression d'un vps_servers supprime ses log_collections (et par
propagation leurs enfants). Les données orphelines deviennent impossibles.
"""
from alembic import op


# revision identifiers
revision = 'b7d4e2a1c9f0'
down_revision = 'f2a9c7b1e3d5'
branch_labels = None
depends_on = None


# (table, nom_contrainte, colonne_locale, table_ref, colonne_ref)
_FKS = [
    ('endpoint_stats',  'endpoint_stats_collection_id_fkey', 'collection_id', 'log_collections', 'id'),
    ('log_entries',     'log_entries_collection_id_fkey',    'collection_id', 'log_collections', 'id'),
    ('log_summaries',   'log_summaries_collection_id_fkey',  'collection_id', 'log_collections', 'id'),
    ('log_collections', 'log_collections_vps_id_fkey',       'vps_id',        'vps_servers',     'id'),
]


def upgrade() -> None:
    for tbl, name, col, ref, refcol in _FKS:
        op.drop_constraint(name, tbl, type_='foreignkey')
        op.create_foreign_key(name, tbl, ref, [col], [refcol], ondelete='CASCADE')


def downgrade() -> None:
    for tbl, name, col, ref, refcol in _FKS:
        op.drop_constraint(name, tbl, type_='foreignkey')
        op.create_foreign_key(name, tbl, ref, [col], [refcol])
