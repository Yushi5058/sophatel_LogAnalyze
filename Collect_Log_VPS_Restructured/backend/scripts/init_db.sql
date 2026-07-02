-- ============================================================
-- Sophatel VPS Log - Initialisation PostgreSQL
-- ============================================================

-- Créer l'utilisateur et la base si nécessaire (à exécuter en tant que superuser)
-- psql -U postgres -f init_db.sql

DO $$
BEGIN
    IF NOT EXISTS (SELECT FROM pg_catalog.pg_roles WHERE rolname = 'sophatel') THEN
        CREATE ROLE sophatel WITH LOGIN PASSWORD 'sophatel';
    END IF;
END
$$;

SELECT 'CREATE DATABASE sophatel_v2 OWNER sophatel'
WHERE NOT EXISTS (SELECT FROM pg_database WHERE datname = 'sophatel_v2')\gexec

GRANT ALL PRIVILEGES ON DATABASE sophatel_v2 TO sophatel;

-- Se connecter à la base (lancer ensuite : \c sophatel_v2)
-- Les tables sont créées automatiquement par SQLAlchemy au démarrage de FastAPI.
-- Ce script n'est nécessaire que pour la création initiale de l'utilisateur/base.

-- Extensions utiles
\c sophatel_v2
CREATE EXTENSION IF NOT EXISTS pg_trgm;   -- recherche full-text rapide
CREATE EXTENSION IF NOT EXISTS btree_gin; -- index combinés

-- Vue pratique : résumé par VPS
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
ORDER BY last_collected DESC;

-- Vue : top 20 chemins globaux
CREATE OR REPLACE VIEW v_top_paths AS
SELECT
    path,
    COUNT(*) AS hits,
    ROUND(100.0 * COUNT(*) / SUM(COUNT(*)) OVER (), 2) AS pct
FROM log_entries
WHERE path IS NOT NULL
GROUP BY path
ORDER BY hits DESC
LIMIT 20;

\echo '✓ Base sophatel_v2 initialisée avec succès'
