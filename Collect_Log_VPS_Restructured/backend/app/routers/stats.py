from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from sqlalchemy import func, case, select
from typing import Optional
from app.core.database import get_db
from app.models.models import LogEntry, LogCollection, LogSummary, VPSServer
from app.schemas.schemas import GlobalStats

router = APIRouter()


def _active_collection_ids(db, vps_id=None):
    """
    Sous-requête des IDs de collections appartenant à des VPS ACTIFS
    (deleted_at IS NULL). Les statistiques excluent ainsi les VPS supprimés
    logiquement. Filtre en plus sur un vps_id précis si fourni.
    """
    q = (
        select(LogCollection.id)
        .join(VPSServer, VPSServer.id == LogCollection.vps_id)
        .where(VPSServer.deleted_at.is_(None))
    )
    if vps_id:
        q = q.where(LogCollection.vps_id == vps_id)
    return q


@router.get("/global", response_model=GlobalStats)
def global_stats(vps_id: Optional[int] = None, db: Session = Depends(get_db)):
    """KPIs globaux pour le dashboard — inclut latences P50/P95/P99 et taux 4xx/5xx"""

    # IDs des collections rattachées à des VPS actifs (exclut les supprimés).
    active_ids = _active_collection_ids(db, vps_id)

    # ── Base query sur LogSummary pour les compteurs ─────────────────────────
    sq = db.query(LogSummary).filter(LogSummary.collection_id.in_(active_ids))

    total_requests = sq.with_entities(func.sum(LogSummary.total_requests)).scalar() or 0
    total_errors   = sq.with_entities(func.sum(LogSummary.error_count)).scalar() or 0
    unique_ips     = sq.with_entities(func.sum(LogSummary.unique_ips)).scalar() or 0
    collections    = sq.with_entities(func.count(LogSummary.id)).scalar() or 0
    vps_count      = db.query(func.count(VPSServer.id)).filter(VPSServer.deleted_at.is_(None)).scalar() or 0
    error_rate     = round(total_errors / total_requests * 100, 2) if total_requests else 0.0

    # ── Latences depuis log_entries ───────────────────────────────────────────
    eq = db.query(LogEntry).filter(
        LogEntry.response_time.isnot(None),
        LogEntry.collection_id.in_(active_ids),
    )

    # Moyenne + percentiles calculés côté PostgreSQL (percentile_cont),
    # sans charger toutes les latences en mémoire.
    avg_s, p50_s, p95_s, p99_s = eq.with_entities(
        func.avg(LogEntry.response_time),
        func.percentile_cont(0.50).within_group(LogEntry.response_time.asc()),
        func.percentile_cont(0.95).within_group(LogEntry.response_time.asc()),
        func.percentile_cont(0.99).within_group(LogEntry.response_time.asc()),
    ).one()

    def _ms(v):
        return round(v * 1000, 1) if v is not None else None  # secondes → ms

    avg_latency = _ms(avg_s)
    p50 = _ms(p50_s)
    p95 = _ms(p95_s)
    p99 = _ms(p99_s)

    # ── Taux 4xx et 5xx ───────────────────────────────────────────────────────
    eq2 = db.query(LogEntry).filter(LogEntry.collection_id.in_(active_ids))

    total_with_status = eq2.filter(LogEntry.status.isnot(None)).count() or 0
    count_4xx = eq2.filter(LogEntry.status >= 400, LogEntry.status < 500).count()
    count_5xx = eq2.filter(LogEntry.status >= 500).count()

    rate_4xx = round(count_4xx / total_with_status * 100, 1) if total_with_status else 0.0
    rate_5xx = round(count_5xx / total_with_status * 100, 1) if total_with_status else 0.0

    return GlobalStats(
        total_requests   = total_requests,
        total_errors     = total_errors,
        unique_ips       = unique_ips,
        collections_count= collections,
        vps_count        = vps_count,
        error_rate       = error_rate,
        avg_latency      = avg_latency,
        p50_latency      = p50,
        p95_latency      = p95,
        p99_latency      = p99,
        rate_4xx         = rate_4xx,
        rate_5xx         = rate_5xx,
    )


@router.get("/status-distribution")
def status_distribution(vps_id: Optional[int] = None, db: Session = Depends(get_db)):
    q = db.query(LogEntry.status, func.count(LogEntry.id)).filter(
        LogEntry.collection_id.in_(_active_collection_ids(db, vps_id))
    )
    rows = q.group_by(LogEntry.status).order_by(LogEntry.status).all()
    return [{"status": r[0], "count": r[1]} for r in rows]


@router.get("/top-paths")
def top_paths(limit: int = 10, vps_id: Optional[int] = None, db: Session = Depends(get_db)):
    q = db.query(LogEntry.path, func.count(LogEntry.id).label("hits")).filter(
        LogEntry.collection_id.in_(_active_collection_ids(db, vps_id))
    )
    rows = q.group_by(LogEntry.path).order_by(func.count(LogEntry.id).desc()).limit(limit).all()
    return [{"path": r[0], "hits": r[1]} for r in rows]


@router.get("/top-ips")
def top_ips(limit: int = 10, vps_id: Optional[int] = None, db: Session = Depends(get_db)):
    q = db.query(LogEntry.ip, func.count(LogEntry.id).label("requests")).filter(
        LogEntry.collection_id.in_(_active_collection_ids(db, vps_id))
    )
    rows = q.group_by(LogEntry.ip).order_by(func.count(LogEntry.id).desc()).limit(limit).all()
    return [{"ip": r[0], "requests": r[1]} for r in rows]


@router.get("/requests-over-time")
def requests_over_time(vps_id: Optional[int] = None, db: Session = Depends(get_db)):
    q = db.query(
        func.date_trunc("hour", LogEntry.timestamp).label("hour"),
        func.count(LogEntry.id).label("count")
    ).filter(
        LogEntry.timestamp.isnot(None),
        LogEntry.collection_id.in_(_active_collection_ids(db, vps_id)),
    )
    rows = q.group_by("hour").order_by("hour").all()
    return [{"hour": str(r[0]), "count": r[1]} for r in rows]


@router.get("/endpoints")
def endpoints_stats(limit: int = 10, vps_id: Optional[int] = None, db: Session = Depends(get_db)):
    """Métriques détaillées par endpoint : avg, p95, p99, max latence, nb requêtes, taux erreur"""
    q = db.query(LogEntry).filter(
        LogEntry.path.isnot(None),
        LogEntry.collection_id.in_(_active_collection_ids(db, vps_id)),
    )

    # Agrégation par chemin côté PostgreSQL (comptage, taux d'erreur, percentiles).
    rows = (
        q.with_entities(
            LogEntry.path.label("path"),
            func.count(LogEntry.id).label("requests"),
            func.sum(case((LogEntry.status >= 400, 1), else_=0)).label("errors"),
            func.avg(LogEntry.response_time).label("avg_rt"),
            func.percentile_cont(0.95).within_group(LogEntry.response_time.asc()).label("p95"),
            func.percentile_cont(0.99).within_group(LogEntry.response_time.asc()).label("p99"),
            func.max(LogEntry.response_time).label("max_rt"),
        )
        .group_by(LogEntry.path)
        .order_by(func.count(LogEntry.id).desc())
        .limit(limit)
        .all()
    )

    def _ms(v):
        return round(v * 1000, 1) if v is not None else None

    return [
        {
            "path":        r.path,
            "requests":    r.requests,
            "error_rate":  round((r.errors or 0) / r.requests * 100, 1) if r.requests else 0.0,
            "avg_latency": _ms(r.avg_rt),
            "p95_latency": _ms(r.p95),
            "p99_latency": _ms(r.p99),
            "max_latency": _ms(r.max_rt),
        }
        for r in rows
    ]


@router.get("/alerts")
def get_alerts(vps_id: Optional[int] = None, db: Session = Depends(get_db)):
    """
    Génère des alertes automatiques basées sur les seuils :
    - Taux 5xx > 5%  → critique
    - Taux 4xx > 20% → avertissement
    - P99 latence > 2000ms → critique
    - P95 latence > 1000ms → avertissement
    - Taux erreur global > 30% → critique
    """
    from datetime import timezone

    active_ids = _active_collection_ids(db, vps_id)
    q  = db.query(LogEntry).filter(LogEntry.collection_id.in_(active_ids))
    sq = db.query(LogSummary).filter(LogSummary.collection_id.in_(active_ids))

    total   = q.filter(LogEntry.status.isnot(None)).count() or 0
    c_4xx   = q.filter(LogEntry.status >= 400, LogEntry.status < 500).count()
    c_5xx   = q.filter(LogEntry.status >= 500).count()
    rate_4xx = round(c_4xx / total * 100, 1) if total else 0
    rate_5xx = round(c_5xx / total * 100, 1) if total else 0

    total_req = sq.with_entities(func.sum(LogSummary.total_requests)).scalar() or 0
    total_err = sq.with_entities(func.sum(LogSummary.error_count)).scalar() or 0
    error_rate = round(total_err / total_req * 100, 1) if total_req else 0

    # Percentiles calculés côté PostgreSQL (pas de chargement en mémoire)
    p95_s, p99_s = (
        q.filter(LogEntry.response_time.isnot(None))
         .with_entities(
             func.percentile_cont(0.95).within_group(LogEntry.response_time.asc()),
             func.percentile_cont(0.99).within_group(LogEntry.response_time.asc()),
         ).one()
    )
    p95 = round(p95_s * 1000, 1) if p95_s is not None else 0
    p99 = round(p99_s * 1000, 1) if p99_s is not None else 0

    now = "maintenant"
    alerts = []

    if rate_5xx > 5:
        alerts.append({
            "severity":     "critical",
            "title":        f"Taux d'erreurs 5xx élevé : {rate_5xx}%",
            "type":         "5xx",
            "value":        rate_5xx,
            "triggered_at": now,
        })

    if rate_4xx > 20:
        alerts.append({
            "severity":     "warning",
            "title":        f"Taux d'erreurs 4xx élevé : {rate_4xx}%",
            "type":         "4xx",
            "value":        rate_4xx,
            "triggered_at": now,
        })

    if p99 > 2000:
        alerts.append({
            "severity":     "critical",
            "title":        f"Latence P99 critique : {p99}ms",
            "type":         "p99",
            "value":        p99,
            "triggered_at": now,
        })
    elif p95 > 1000:
        alerts.append({
            "severity":     "warning",
            "title":        f"Latence P95 dégradée : {p95}ms",
            "type":         "p99",
            "value":        p95,
            "triggered_at": now,
        })

    if error_rate > 30:
        alerts.append({
            "severity":     "critical",
            "title":        f"Taux d'erreur global critique : {error_rate}%",
            "type":         "5xx",
            "value":        error_rate,
            "triggered_at": now,
        })

    return alerts