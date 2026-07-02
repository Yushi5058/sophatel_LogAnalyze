"""
backend/app/core/scheduler.py

Planificateur APScheduler intégré dans FastAPI.
Lance automatiquement la collecte SSH et l'analyse
selon les intervalles définis dans .env.

Installation :
    pip install apscheduler==3.10.4
"""

import logging
import sys
from pathlib import Path

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger
from apscheduler.triggers.cron import CronTrigger

# ── Imports internes ──────────────────────────────────────────────────────────
ROOT = Path(__file__).resolve().parents[3]   # racine du projet
sys.path.insert(0, str(ROOT))

from src.config import config, load_vps_inventory
from src.collector.runner import run_collection
from src.analyzer.analyze import run_analysis        # à créer (voir ci-dessous)

logger = logging.getLogger("scheduler")

# ── Instance globale du scheduler ─────────────────────────────────────────────
scheduler = AsyncIOScheduler(timezone="Africa/Casablanca")


# ── Tâche 1 : Collecte des logs ───────────────────────────────────────────────
async def job_collect():
    """Récupère les logs de tous les VPS définis dans config/vps.yaml."""
    logger.info("[Scheduler] Démarrage de la collecte...")
    try:
        vps_list = load_vps_inventory()
        results = run_collection(vps_list, use_mock=config.USE_MOCK)
        ok  = [r["vps"] for r in results if r["ok"]]
        nok = [r["vps"] for r in results if not r["ok"]]
        logger.info(f"[Scheduler] Collecte terminée — OK: {ok}  ERREUR: {nok}")
    except Exception as e:
        logger.error(f"[Scheduler] Erreur collecte : {e}", exc_info=True)


# ── Tâche 2 : Analyse et stockage en base ─────────────────────────────────────
async def job_analyze():
    """Parse les CSV collectés et insère les données dans PostgreSQL."""
    logger.info("[Scheduler] Démarrage de l'analyse...")
    try:
        run_analysis()   # lit logs/<vps>/*.csv et peuple la DB
        logger.info("[Scheduler] Analyse terminée.")
    except Exception as e:
        logger.error(f"[Scheduler] Erreur analyse : {e}", exc_info=True)


# ── Enregistrement des jobs ───────────────────────────────────────────────────
def register_jobs():
    """
    Planifie les deux tâches.

    Intervalles configurables via .env :
        COLLECT_INTERVAL_MINUTES=30   (défaut : toutes les 30 min)
        ANALYZE_CRON=*/35 * * * *     (défaut : 5 min après la collecte)
    """
    import os

    collect_minutes = int(os.getenv("COLLECT_INTERVAL_MINUTES", "30"))
    analyze_cron    = os.getenv("ANALYZE_CRON", "5-59/35 * * * *")

    # Collecte toutes les N minutes
    scheduler.add_job(
        job_collect,
        trigger=IntervalTrigger(minutes=collect_minutes),
        id="collect_logs",
        name="Collecte SSH des logs Nginx",
        replace_existing=True,
        misfire_grace_time=60,
    )

    # Analyse selon expression cron (5 min après la collecte par défaut)
    scheduler.add_job(
        job_analyze,
        trigger=CronTrigger.from_crontab(analyze_cron),
        id="analyze_logs",
        name="Analyse et stockage en base",
        replace_existing=True,
        misfire_grace_time=120,
    )

    logger.info(
        f"[Scheduler] Jobs enregistrés — "
        f"collecte toutes les {collect_minutes} min | "
        f"analyse cron: '{analyze_cron}'"
    )