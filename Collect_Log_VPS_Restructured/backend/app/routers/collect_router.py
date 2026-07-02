"""
backend/app/api/collect.py
Route POST /api/collect/{vps_id}
Collecte les logs du VPS via SSH (ou mock) et les écrit en CSV.
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.models import VPSServer

# ── Import du runner ──────────────────────────────────────────────────────────
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "src"))

from src.collector.runner import collect_ssh, collect_mock
from src.config import config

router = APIRouter()


@router.post("/{vps_id}")
def collect_logs(vps_id: int, db: Session = Depends(get_db)):
    # 1. Récupérer le VPS en base
    vps = db.query(VPSServer).filter(VPSServer.id == vps_id).first()
    if not vps:
        raise HTTPException(status_code=404, detail="VPS introuvable")

    try:
        # 2. Collecte mock ou SSH selon config
        if config.USE_MOCK:
            log_path, csv_path = collect_mock(vps_name=vps.name)
        else:
            # Vérifications obligatoires
            if not vps.host:
                raise ValueError("Hôte SSH manquant pour ce VPS")
            if not vps.user or vps.user == "unknown":
                raise ValueError(
                    f"Utilisateur SSH invalide ('{vps.user}'). "
                    "Modifiez le VPS et renseignez un utilisateur SSH valide."
                )

            log_path, csv_path = collect_ssh(
                vps_name=vps.name,
                host=vps.host,
                user=vps.user,
                port=vps.port or 22,
                key_path=getattr(vps, "key_path", None) or "~/.ssh/id_rsa",
                log_path=vps.log_path or "/var/log/nginx/access.log",
                passphrase=getattr(vps, "password", None) or None,
            )

        # 3. Compter les lignes collectées depuis le CSV
        lines_collected = 0
        if csv_path.exists():
            with open(csv_path, encoding="utf-8") as f:
                # -1 pour exclure l'en-tête CSV
                lines_collected = max(0, sum(1 for _ in f) - 1)

        return {
            "success": True,
            "message": f"Collecte terminée pour {vps.name}",
            "lines_collected": lines_collected,
            "csv_path": str(csv_path),
            "log_path": str(log_path),
        }

    except ValueError as exc:
        # Erreur de configuration (user manquant, host manquant…)
        raise HTTPException(status_code=422, detail=str(exc))

    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=f"Erreur collecte SSH pour '{vps.name}' : {exc}"
        )