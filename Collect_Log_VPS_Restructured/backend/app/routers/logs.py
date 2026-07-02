from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.orm import Session
from typing import Optional
from app.core.database import get_db
from app.models.models import LogEntry, LogCollection, LogSummary
from app.schemas.schemas import LogEntryOut, CollectionOut, LogSummaryOut, PaginatedLogs

router = APIRouter()


@router.get("/collections", response_model=list[CollectionOut])
def get_collections(
    vps_id: Optional[int] = None,
    limit: int = Query(50, le=200),
    db: Session = Depends(get_db)
):
    """Liste toutes les sessions de collecte"""
    q = db.query(LogCollection)
    if vps_id:
        q = q.filter(LogCollection.vps_id == vps_id)
    return q.order_by(LogCollection.collected_at.desc()).limit(limit).all()


@router.get("/collections/{collection_id}", response_model=CollectionOut)
def get_collection(collection_id: int, db: Session = Depends(get_db)):
    col = db.query(LogCollection).filter(LogCollection.id == collection_id).first()
    if not col:
        raise HTTPException(status_code=404, detail="Collection introuvable")
    return col


@router.get("/collections/{collection_id}/entries", response_model=PaginatedLogs)
def get_entries(
    collection_id: int,
    page: int = Query(1, ge=1),
    size: int = Query(100, le=500),
    status: Optional[int] = None,
    method: Optional[str] = None,
    ip: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """Entrées paginées d'une collection avec filtres"""
    q = db.query(LogEntry).filter(LogEntry.collection_id == collection_id)
    if status:
        q = q.filter(LogEntry.status == status)
    if method:
        q = q.filter(LogEntry.method == method.upper())
    if ip:
        q = q.filter(LogEntry.ip == ip)

    total = q.count()
    items = q.offset((page - 1) * size).limit(size).all()
    return PaginatedLogs(total=total, page=page, size=size, items=items)


@router.get("/collections/{collection_id}/summary", response_model=LogSummaryOut)
def get_summary(collection_id: int, db: Session = Depends(get_db)):
    """Résumé analytique d'une collection"""
    summary = db.query(LogSummary).filter(LogSummary.collection_id == collection_id).first()
    if not summary:
        raise HTTPException(status_code=404, detail="Aucun résumé pour cette collection")
    return summary
