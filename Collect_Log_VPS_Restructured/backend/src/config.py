"""
src/config.py
Chargement de la configuration depuis .env et config/vps.yaml
"""
import os
from pathlib import Path
import yaml
from dotenv import load_dotenv

# Racine du projet
ROOT = Path(__file__).resolve().parents[1]
load_dotenv(ROOT / ".env")


class AppConfig:
    """Configuration globale de l'application"""

    # PostgreSQL
    DATABASE_URL = os.getenv("DATABASE_URL")

    # Chemins
    LOG_DIR:  Path = ROOT / os.getenv("LOG_DIR", "logs")
    DATA_DIR: Path = ROOT / os.getenv("DATA_DIR", "data")

    # Mode
    USE_MOCK: bool = os.getenv("USE_MOCK", "false").lower() == "true"
    DEBUG:    bool = os.getenv("DEBUG", "false").lower() == "true"

    # SSH
    SSH_KEY_PATH:   str = os.getenv("SSH_KEY_PATH", "~/.ssh/id_rsa")
    SSH_PASSPHRASE: str = os.getenv("SSH_PASSPHRASE", "")
    # Vérification de la clé d'hôte (anti-MITM)
    SSH_KNOWN_HOSTS: str = os.getenv("SSH_KNOWN_HOSTS", "~/.ssh/known_hosts")
    SSH_STRICT_HOST_KEY: bool = os.getenv("SSH_STRICT_HOST_KEY", "false").lower() == "true"


def load_vps_inventory(path: str | None = None) -> list[dict]:
    """
    Charge l'inventaire des VPS depuis config/vps.yaml.
    Retourne une liste de dicts avec les clés :
        name, host, user, port, key_path, log_path
    """
    yaml_path = Path(path) if path else ROOT / "config" / "vps.yaml"
    if not yaml_path.exists():
        raise FileNotFoundError(f"Inventaire VPS introuvable : {yaml_path}")

    with open(yaml_path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)

    return data.get("vps", [])


# Instance globale
config = AppConfig()