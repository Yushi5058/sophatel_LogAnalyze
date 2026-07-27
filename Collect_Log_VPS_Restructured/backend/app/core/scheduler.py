"""
backend/app/core/scheduler.py

Planificateur APScheduler intégré dans FastAPI.
Lance automatiquement la collecte SSH et l'analyse
selon les intervalles définis dans .env.

Installation :
    pip install apscheduler==3.10.4
"""

import logging

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.jobstores.sqlalchemy import SQLAlchemyJobStore
from apscheduler.triggers.interval import IntervalTrigger
from apscheduler.triggers.cron import CronTrigger

# Engine SQLAlchemy central réutilisé pour le store des jobs (pas de second pool).
from app.core.database import engine
# Paquets `app` et `src` résolus depuis backend/ (répertoire de lancement de l'API)
from src.config import config
from src.collector.runner import run_collection
from src.analyzer.analyze import run_analysis        # à créer (voir ci-dessous)


def _load_vps_from_db() -> list[dict]:
    """Inventaire des VPS depuis la base (source de vérité de l'UI/API)."""
    from app.core.database import SessionLocal
    from app.models.models import VPSServer

    db = SessionLocal()
    try:
        return [
            {
                "name": v.name,
                "host": v.host,
                "user": v.user,
                "port": v.port or 22,
                "log_path": v.log_path or "/var/log/nginx/access.log",
                "password": v.password or None,   # déchiffré par l'ORM (RM-06)
                "ssh_key": v.ssh_key or None,
                "collect_offset": v.collect_offset or 0,   # curseur incrémental
            }
            for v in db.query(VPSServer).filter(VPSServer.deleted_at.is_(None)).all()
        ]
    finally:
        db.close()

def _persist_offsets(results: list[dict]) -> None:
    """Enregistre le nouvel offset de collecte par VPS (curseur incrémental)."""
    updates = [
        (r["vps"], r["new_offset"])
        for r in results
        if r.get("ok") and r.get("new_offset") is not None
    ]
    if not updates:
        return
    from app.core.database import SessionLocal
    from app.models.models import VPSServer

    db = SessionLocal()
    try:
        for name, offset in updates:
            db.query(VPSServer).filter(
                VPSServer.name == name, VPSServer.deleted_at.is_(None)
            ).update({VPSServer.collect_offset: offset}, synchronize_session=False)
        db.commit()
    finally:
        db.close()


logger = logging.getLogger("scheduler")

# ── Instance globale du scheduler ─────────────────────────────────────────────
# Jobs PERSISTÉS en PostgreSQL (RM-26) : ils survivent aux redémarrages de l'API
# (table `apscheduler_jobs`, créée automatiquement au premier démarrage).
#   - coalesce=True      : après une coupure, une seule exécution rattrape les runs manqués
#                          (pas de rafale), en complément de misfire_grace_time.
#   - max_instances=1    : jamais deux exécutions simultanées du même job.
scheduler = AsyncIOScheduler(
    jobstores={"default": SQLAlchemyJobStore(engine=engine)},
    job_defaults={"coalesce": True, "max_instances": 1},
    timezone="Africa/Casablanca",
)


# ── Tâche 1 : Collecte des logs ───────────────────────────────────────────────
async def job_collect():
    """Récupère les logs de tous les VPS enregistrés en base (via l'UI/API)."""
    logger.info("[Scheduler] Démarrage de la collecte...")
    try:
        vps_list = _load_vps_from_db()
        if not vps_list:
            logger.info("[Scheduler] Aucun VPS en base — collecte ignorée.")
            return
        results = run_collection(vps_list, use_mock=config.USE_MOCK)
        _persist_offsets(results)
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