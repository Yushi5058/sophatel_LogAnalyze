"""Routes d'enrichissement des IP (RM-34) : géolocalisation + réputation."""
from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.models import LogEntry
from app.routers.stats import _active_collection_ids  # exclut les VPS supprimés
from app.services.enrichment_service import enrich_ip, enrich_ips

router = APIRouter()


@router.get("/ip/{ip}")
def get_ip_enrichment(ip: str, db: Session = Depends(get_db)):
    """Enrichissement (cache ou API externes) d'une IP donnée."""
    return enrich_ip(ip, db)


@router.get("/top-ips")
def top_ips_enriched(
    limit: int = Query(10, ge=1, le=50),
    vps_id: Optional[int] = None,
    db: Session = Depends(get_db),
):
    """Top IP des logs (VPS actifs) enrichies (pays, réputation…)."""
    rows = (
        db.query(LogEntry.ip, func.count(LogEntry.id).label("requests"))
        .filter(
            LogEntry.ip.isnot(None),
            LogEntry.collection_id.in_(_active_collection_ids(db, vps_id)),
        )
        .group_by(LogEntry.ip)
        .order_by(func.count(LogEntry.id).desc())
        .limit(limit)
        .all()
    )
    ips = [r[0] for r in rows]
    enr = {e["ip"]: e for e in enrich_ips(ips, db)}
    return [
        {"ip": r[0], "requests": r[1],
         **{k: v for k, v in enr.get(r[0], {}).items() if k != "ip"}}
        for r in rows
    ]
