"""
backend/app/api/collect.py
Route POST /api/collect/{vps_id}
Collecte les logs du VPS via SSH (ou mock) et les écrit en CSV.
"""

import logging
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import require_role
from app.core.config import settings
from app.models.models import VPSServer

logger = logging.getLogger(__name__)

# Paquets `app` et `src` résolus depuis backend/ (répertoire de lancement de l'API)
from src.collector.runner import collect_ssh, collect_mock
from src.config import config

router = APIRouter()


@router.post("/{vps_id}")
def collect_logs(vps_id: int, db: Session = Depends(get_db),
                 _admin=Depends(require_role("admin"))):
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
                key_path=config.SSH_KEY_PATH,          # repli : clé locale
                log_path=vps.log_path or "/var/log/nginx/access.log",
                password=vps.password or None,          # mot de passe de connexion (déchiffré)
                ssh_key=vps.ssh_key or None,            # clé privée stockée en base (déchiffrée)
                passphrase=config.SSH_PASSPHRASE or None,  # passphrase de la clé si besoin
                known_hosts=config.SSH_KNOWN_HOSTS,        # vérif d'identité (anti-MITM)
                strict_host_key=config.SSH_STRICT_HOST_KEY,
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
        # Détail complet en logs serveur ; message générique au client (sauf DEBUG).
        logger.exception("Erreur collecte SSH pour '%s'", vps.name)
        detail = (
            f"Erreur collecte pour '{vps.name}' : {exc}"
            if settings.DEBUG
            else f"Erreur interne lors de la collecte pour '{vps.name}'."
        )
        raise HTTPException(status_code=500, detail=detail)