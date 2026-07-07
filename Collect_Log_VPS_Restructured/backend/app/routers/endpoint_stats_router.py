"""
backend/app/routers/endpoint_stats_router.py

GET  /api/endpoint-stats                         → liste filtrée
GET  /api/endpoint-stats/collection/{id}         → stats d'une collection
POST /api/endpoint-stats/compute/{collection_id} → calcul à la demande
"""
from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.orm import Session
from typing import Optional, List

from app.core.database import get_db
from app.core.security import require_role
from app.models.models import EndpointStat, LogCollection
from app.schemas.schemas import EndpointStatOut
from app.services.endpoint_stats_service import compute_endpoint_stats

router = APIRouter()


@router.get("/", response_model=List[EndpointStatOut])
def list_endpoint_stats(
    vps_id:       Optional[int]  = None,
    collection_id: Optional[int] = None,
    endpoint:     Optional[str]  = None,
    sort_by:      str            = Query("nb_requetes", description="Colonne de tri"),
    order:        str            = Query("desc", regex="^(asc|desc)$"),
    limit:        int            = Query(100, le=1000),
    offset:       int            = 0,
    db:           Session        = Depends(get_db),
):
    """
    Retourne les stats d'endpoint avec filtres et tri.
    Filtre par vps_id, collection_id ou recherche partielle d'endpoint.
    """
    q = db.query(EndpointStat)

    if vps_id:
        col_ids = db.query(LogCollection.id).filter(LogCollection.vps_id == vps_id).subquery()
        q = q.filter(EndpointStat.collection_id.in_(col_ids))

    if collection_id:
        q = q.filter(EndpointStat.collection_id == collection_id)

    if endpoint:
        q = q.filter(EndpointStat.endpoint.ilike(f"%{endpoint}%"))

    # Tri dynamique
    allowed_sort = {
        "nb_requetes", "latence_moy_ms", "latence_p50_ms", "latence_p95_ms",
        "latence_p99_ms", "latence_max_ms", "taux_erreur_4xx", "taux_erreur_5xx",
        "body_moy_mo", "premiere_occurrence_utc", "derniere_occurrence_utc",
    }
    if sort_by in allowed_sort:
        col = getattr(EndpointStat, sort_by)
        q = q.order_by(col.desc() if order == "desc" else col.asc())

    return q.offset(offset).limit(limit).all()


@router.get("/collection/{collection_id}", response_model=List[EndpointStatOut])
def stats_by_collection(collection_id: int, db: Session = Depends(get_db)):
    """Toutes les stats d'endpoint pour une collection."""
    rows = (
        db.query(EndpointStat)
        .filter(EndpointStat.collection_id == collection_id)
        .order_by(EndpointStat.nb_requetes.desc())
        .all()
    )
    return rows


@router.post("/compute/{collection_id}")
def compute_stats(collection_id: int, db: Session = Depends(get_db),
                  _admin=Depends(require_role("admin"))):
    """
    Déclenche manuellement le calcul des stats d'endpoint
    pour une collection existante.
    """
    coll = db.query(LogCollection).filter(LogCollection.id == collection_id).first()
    if not coll:
        raise HTTPException(status_code=404, detail="Collection introuvable")

    count = compute_endpoint_stats(collection_id, db)
    db.commit()
    return {"ok": True, "collection_id": collection_id, "endpoints_computed": count}