"""extensions_and_views

Revision ID: 7fd3b5d36be0
Revises: 2cf6f83894e0
Create Date: 2026-07-02 15:54:19.136634

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers
revision = '7fd3b5d36be0'
down_revision = '2cf6f83894e0'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS pg_trgm")
    op.execute("CREATE EXTENSION IF NOT EXISTS btree_gin")
    op.execute("""
        CREATE OR REPLACE VIEW v_vps_summary AS
        SELECT
            v.name                          AS vps_name,
            COUNT(DISTINCT c.id)           AS nb_collections,
            SUM(s.total_requests)          AS total_requests,
            SUM(s.error_count)             AS total_errors,
            ROUND(AVG(s.avg_resp_time)::numeric, 3) AS avg_resp_time,
            MAX(c.collected_at)            AS last_collected
        FROM vps_servers v
        LEFT JOIN log_collections c ON c.vps_id = v.id
        LEFT JOIN log_summaries   s ON s.collection_id = c.id
        GROUP BY v.name
        ORDER BY last_collected DESC
    """)
    op.execute("""
        CREATE OR REPLACE VIEW v_top_paths AS
        SELECT
            path,
            COUNT(*) AS hits,
            ROUND(100.0 * COUNT(*) / SUM(COUNT(*)) OVER (), 2) AS pct
        FROM log_entries
        WHERE path IS NOT NULL
        GROUP BY path
        ORDER BY hits DESC
        LIMIT 20
    """)


def downgrade() -> None:
    op.execute("DROP VIEW IF EXISTS v_top_paths")
    op.execute("DROP VIEW IF EXISTS v_vps_summary")
