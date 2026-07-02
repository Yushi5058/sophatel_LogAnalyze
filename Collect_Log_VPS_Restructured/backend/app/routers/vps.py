from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.models.models import VPSServer, LogCollection, LogEntry, EndpointStat, LogSummary
from app.schemas.schemas import VPSCreate, VPSUpdate, VPSOut

router = APIRouter()


@router.get("/", response_model=list[VPSOut])
def list_vps(db: Session = Depends(get_db)):
    return db.query(VPSServer).order_by(VPSServer.name).all()


@router.post("/", response_model=VPSOut, status_code=201)
def create_vps(payload: VPSCreate, db: Session = Depends(get_db)):
    existing = db.query(VPSServer).filter(VPSServer.name == payload.name).first()
    if existing:
        raise HTTPException(status_code=409, detail=f"VPS '{payload.name}' déjà enregistré")
    vps = VPSServer(**payload.dict())
    db.add(vps)
    db.commit()
    db.refresh(vps)
    return vps


@router.get("/{vps_id}", response_model=VPSOut)
def get_vps(vps_id: int, db: Session = Depends(get_db)):
    vps = db.query(VPSServer).filter(VPSServer.id == vps_id).first()
    if not vps:
        raise HTTPException(status_code=404, detail="VPS introuvable")
    return vps


@router.put("/{vps_id}", response_model=VPSOut)
def update_vps(vps_id: int, payload: VPSUpdate, db: Session = Depends(get_db)):
    vps = db.query(VPSServer).filter(VPSServer.id == vps_id).first()
    if not vps:
        raise HTTPException(status_code=404, detail="VPS introuvable")
    if payload.name and payload.name != vps.name:
        conflict = db.query(VPSServer).filter(VPSServer.name == payload.name).first()
        if conflict:
            raise HTTPException(status_code=409, detail=f"VPS '{payload.name}' déjà enregistré")
    for field, value in payload.dict(exclude_unset=True).items():
        setattr(vps, field, value)
    db.commit()
    db.refresh(vps)
    return vps


@router.delete("/{vps_id}", status_code=204)
def delete_vps(vps_id: int, db: Session = Depends(get_db)):
    vps = db.query(VPSServer).filter(VPSServer.id == vps_id).first()
    if not vps:
        raise HTTPException(status_code=404, detail="VPS introuvable")

    # Récupérer les IDs de toutes les collections liées à ce VPS
    col_ids = [c.id for c in db.query(LogCollection.id).filter(
        LogCollection.vps_id == vps_id).all()]

    if col_ids:
        # Supprimer dans l'ordre enfants → parents (sans passer par la session ORM)
        db.query(LogEntry).filter(
            LogEntry.collection_id.in_(col_ids)
        ).delete(synchronize_session=False)

        db.query(EndpointStat).filter(
            EndpointStat.collection_id.in_(col_ids)
        ).delete(synchronize_session=False)

        db.query(LogSummary).filter(
            LogSummary.collection_id.in_(col_ids)
        ).delete(synchronize_session=False)

        db.query(LogCollection).filter(
            LogCollection.vps_id == vps_id
        ).delete(synchronize_session=False)

    db.delete(vps)
    db.commit()