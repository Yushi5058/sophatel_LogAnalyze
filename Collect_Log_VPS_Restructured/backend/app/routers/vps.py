from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Response
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.security import require_role
from app.models.models import VPSServer
from app.schemas.schemas import VPSCreate, VPSUpdate, VPSOut

router = APIRouter()


@router.get("/", response_model=list[VPSOut])
def list_vps(
    response: Response,
    skip: int = Query(0, ge=0, description="Nombre d'éléments à sauter"),
    limit: Optional[int] = Query(
        None, ge=1, le=500,
        description="Taille de page ; absent = tous les VPS (rétrocompatible)",
    ),
    db: Session = Depends(get_db),
):
    """
    Liste des VPS actifs, paginable (RM-24).

    - `skip` / `limit` optionnels ; sans `limit`, renvoie tout (comportement
      historique préservé pour le frontend existant).
    - Le nombre total de VPS actifs est renvoyé dans l'en-tête `X-Total-Count`
      (exposé via CORS), pour construire une pagination côté client.
    """
    base = db.query(VPSServer).filter(VPSServer.deleted_at.is_(None))
    total = base.count()
    response.headers["X-Total-Count"] = str(total)

    q = base.order_by(VPSServer.name).offset(skip)
    if limit is not None:
        q = q.limit(limit)
    return q.all()


@router.get("/deleted", response_model=list[VPSOut])
def list_deleted_vps(db: Session = Depends(get_db),
                     _admin=Depends(require_role("admin"))):
    """Liste les VPS supprimés logiquement (pour restauration)."""
    return (
        db.query(VPSServer)
        .filter(VPSServer.deleted_at.isnot(None))
        .order_by(VPSServer.deleted_at.desc())
        .all()
    )


@router.post("/", response_model=VPSOut, status_code=201)
def create_vps(payload: VPSCreate, db: Session = Depends(get_db),
               _admin=Depends(require_role("admin"))):
    existing = (
        db.query(VPSServer)
        .filter(VPSServer.name == payload.name, VPSServer.deleted_at.is_(None))
        .first()
    )
    if existing:
        raise HTTPException(status_code=409, detail=f"VPS '{payload.name}' déjà enregistré")
    vps = VPSServer(**payload.model_dump())
    db.add(vps)
    db.commit()
    db.refresh(vps)
    return vps


@router.get("/{vps_id}", response_model=VPSOut)
def get_vps(vps_id: int, db: Session = Depends(get_db)):
    vps = (
        db.query(VPSServer)
        .filter(VPSServer.id == vps_id, VPSServer.deleted_at.is_(None))
        .first()
    )
    if not vps:
        raise HTTPException(status_code=404, detail="VPS introuvable")
    return vps


@router.put("/{vps_id}", response_model=VPSOut)
def update_vps(vps_id: int, payload: VPSUpdate, db: Session = Depends(get_db),
               _admin=Depends(require_role("admin"))):
    vps = (
        db.query(VPSServer)
        .filter(VPSServer.id == vps_id, VPSServer.deleted_at.is_(None))
        .first()
    )
    if not vps:
        raise HTTPException(status_code=404, detail="VPS introuvable")
    if payload.name and payload.name != vps.name:
        conflict = (
            db.query(VPSServer)
            .filter(VPSServer.name == payload.name, VPSServer.deleted_at.is_(None))
            .first()
        )
        if conflict:
            raise HTTPException(status_code=409, detail=f"VPS '{payload.name}' déjà enregistré")
    data = payload.model_dump(exclude_unset=True)
    # Changer le fichier de logs invalide le curseur incrémental : on repart de 0.
    if "log_path" in data and data["log_path"] != vps.log_path:
        vps.collect_offset = 0
    for field, value in data.items():
        setattr(vps, field, value)
    db.commit()
    db.refresh(vps)
    return vps


@router.delete("/{vps_id}", status_code=204)
def delete_vps(vps_id: int, db: Session = Depends(get_db),
               _admin=Depends(require_role("admin"))):
    # Suppression LOGIQUE : le VPS et son historique de logs restent en base
    # (config irremplaçable, saisie à la main), récupérables en remettant
    # deleted_at à NULL. Les logs, régénérables, ne sont pas touchés.
    vps = (
        db.query(VPSServer)
        .filter(VPSServer.id == vps_id, VPSServer.deleted_at.is_(None))
        .first()
    )
    if not vps:
        raise HTTPException(status_code=404, detail="VPS introuvable")

    vps.deleted_at = datetime.now(timezone.utc)
    db.commit()


@router.post("/{vps_id}/restore", response_model=VPSOut)
def restore_vps(vps_id: int, db: Session = Depends(get_db),
                _admin=Depends(require_role("admin"))):
    """Annule une suppression logique (remet deleted_at à NULL)."""
    vps = (
        db.query(VPSServer)
        .filter(VPSServer.id == vps_id, VPSServer.deleted_at.isnot(None))
        .first()
    )
    if not vps:
        raise HTTPException(status_code=404, detail="VPS supprimé introuvable")

    # Un VPS actif a pu reprendre ce nom entre-temps : la restauration
    # violerait alors l'unicité partielle. On la bloque avec un message clair.
    conflict = (
        db.query(VPSServer)
        .filter(VPSServer.name == vps.name, VPSServer.deleted_at.is_(None))
        .first()
    )
    if conflict:
        raise HTTPException(
            status_code=409,
            detail=f"Un VPS actif nommé '{vps.name}' existe déjà ; "
                   f"renommez-le avant de restaurer celui-ci.",
        )

    vps.deleted_at = None
    db.commit()
    db.refresh(vps)
    return vps
