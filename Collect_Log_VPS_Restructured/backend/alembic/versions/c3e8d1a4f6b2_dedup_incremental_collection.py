"""déduplication du contenu : collecte incrémentale (offset) + clé naturelle (vps_id, line_hash)

Revision ID: c3e8d1a4f6b2
Revises: b7d4e2a1c9f0
Create Date: 2026-07-21 00:20:00.000000

Corrige la duplication du contenu entre collectes (fenêtre glissante des N
dernières lignes → mêmes lignes réinsérées dans des collections successives) :

- A. `vps_servers.collect_offset` : curseur d'octets pour ne collecter que le
     nouveau contenu depuis la dernière fois.
- B. `log_entries.vps_id` + `log_entries.line_hash` + index UNIQUE
     (vps_id, line_hash) : filet anti-duplication au stockage, par VPS.

Cette migration nettoie aussi les doublons **déjà présents** (on garde la ligne
au plus petit id par (vps_id, line_hash)) et recalcule les compteurs des
`log_summaries` pour que les statistiques ne soient plus gonflées.
NB : le downgrade retire colonnes/index mais ne restaure pas les lignes
supprimées (données de logs régénérables).
"""
from alembic import op
import sqlalchemy as sa


# revision identifiers
revision = 'c3e8d1a4f6b2'
down_revision = 'b7d4e2a1c9f0'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ── A. Curseur de collecte incrémentale ───────────────────────────────────
    op.add_column(
        'vps_servers',
        sa.Column('collect_offset', sa.BigInteger(), nullable=False, server_default='0'),
    )

    # ── B. Clé naturelle sur log_entries ──────────────────────────────────────
    op.add_column('log_entries', sa.Column('vps_id', sa.Integer(), nullable=True))
    op.add_column('log_entries', sa.Column('line_hash', sa.String(length=32), nullable=True))

    # Backfill vps_id depuis la collection parente.
    op.execute("""
        UPDATE log_entries e
        SET vps_id = c.vps_id
        FROM log_collections c
        WHERE e.collection_id = c.id
    """)

    # Backfill line_hash : md5 déterministe des champs stockés (interne à
    # l'historique — suffit à faire collisionner les lignes identiques).
    op.execute("""
        UPDATE log_entries SET line_hash = md5(concat_ws('|',
            coalesce(ip, ''),
            coalesce(timestamp::text, ''),
            coalesce(method, ''),
            coalesce(path, ''),
            coalesce(status::text, ''),
            coalesce(size::text, ''),
            coalesce(referrer, ''),
            coalesce(user_agent, ''),
            coalesce(response_time::text, '')
        ))
    """)

    # Déduplication des lignes déjà en base : garde le plus petit id par
    # (vps_id, line_hash), supprime le reste (doublons de collectes qui se
    # chevauchent). CASCADE non nécessaire (log_entries est une feuille).
    op.execute("""
        DELETE FROM log_entries a
        USING log_entries b
        WHERE a.vps_id = b.vps_id
          AND a.line_hash = b.line_hash
          AND a.id > b.id
    """)

    # Recalcule les compteurs des résumés à partir des lignes dédupliquées.
    op.execute("""
        UPDATE log_summaries s SET
            total_requests = sub.cnt,
            error_count    = sub.err,
            success_count  = sub.ok,
            unique_ips     = sub.uips
        FROM (
            SELECT collection_id,
                   COUNT(*)                                            AS cnt,
                   COUNT(*) FILTER (WHERE status >= 400)               AS err,
                   COUNT(*) FILTER (WHERE status IS NOT NULL AND status < 400) AS ok,
                   COUNT(DISTINCT ip)                                  AS uips
            FROM log_entries
            GROUP BY collection_id
        ) sub
        WHERE s.collection_id = sub.collection_id
    """)
    # Collections entièrement dédupliquées (plus aucune ligne) → compteurs à 0.
    op.execute("""
        UPDATE log_summaries s SET
            total_requests = 0, error_count = 0, success_count = 0, unique_ips = 0
        WHERE NOT EXISTS (
            SELECT 1 FROM log_entries e WHERE e.collection_id = s.collection_id
        )
    """)

    # Colonnes désormais obligatoires + FK + index unique.
    op.alter_column('log_entries', 'vps_id', existing_type=sa.Integer(), nullable=False)
    op.alter_column('log_entries', 'line_hash', existing_type=sa.String(length=32), nullable=False)
    op.create_index('ix_log_entries_vps_id', 'log_entries', ['vps_id'])
    op.create_foreign_key(
        'log_entries_vps_id_fkey', 'log_entries', 'vps_servers',
        ['vps_id'], ['id'], ondelete='CASCADE',
    )
    op.create_index(
        'uq_log_entries_vps_hash', 'log_entries', ['vps_id', 'line_hash'], unique=True,
    )


def downgrade() -> None:
    op.drop_index('uq_log_entries_vps_hash', table_name='log_entries')
    op.drop_constraint('log_entries_vps_id_fkey', 'log_entries', type_='foreignkey')
    op.drop_index('ix_log_entries_vps_id', table_name='log_entries')
    op.drop_column('log_entries', 'line_hash')
    op.drop_column('log_entries', 'vps_id')
    op.drop_column('vps_servers', 'collect_offset')
