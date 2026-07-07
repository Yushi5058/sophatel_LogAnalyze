"""
backend/app/api/analyze.py
Route POST /api/analyze/{vps_id}
Trouve le dernier CSV collecté pour ce VPS et le passe à l'analyseur.
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import require_role
from app.models.models import VPSServer

# ── Import de l'analyseur ─────────────────────────────────────────────────────
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "src"))

from src.analyzer.analyze import analyze_csv
from src.config import config

router = APIRouter()


def _find_latest_csv(vps_name: str) -> Path | None:
    """Retourne le CSV le plus récent dans logs/<vps_name>/."""
    vps_dir = config.LOG_DIR / vps_name
    if not vps_dir.exists():
        return None
    csv_files = sorted(vps_dir.glob("*.csv"), key=lambda p: p.stat().st_mtime, reverse=True)
    return csv_files[0] if csv_files else None


@router.post("/{vps_id}")
def analyze_logs(vps_id: int, db: Session = Depends(get_db),
                 _admin=Depends(require_role("admin"))):
    # 1. Récupérer le VPS
    vps = db.query(VPSServer).filter(VPSServer.id == vps_id).first()
    if not vps:
        raise HTTPException(status_code=404, detail="VPS introuvable")

    try:
        # 2. Trouver le dernier CSV disponible
        csv_path = _find_latest_csv(vps.name)
        if csv_path is None:
            raise HTTPException(
                status_code=404,
                detail=(
                    f"Aucun fichier CSV trouvé pour '{vps.name}'. "
                    "Lancez d'abord une collecte."
                )
            )

        # 3. Lancer l'analyse
        result = analyze_csv(str(csv_path), vps_name=vps.name, mode="ssh")

        return {
            "success": True,
            "message": f"Analyse terminée pour {vps.name}",
            "total_requests": result.get("total_requests", 0),
            "unique_ips":     result.get("unique_ips", 0),
            "error_count":    result.get("error_count", 0),
            "success_count":  result.get("success_count", 0),
            "error_rate":     result.get("error_rate", 0.0),
            "collection_id":  result.get("collection_id"),
        }

    except HTTPException:
        raise  # laisser passer les 404 explicites

    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=f"Erreur analyse pour '{vps.name}' : {exc}"
        )