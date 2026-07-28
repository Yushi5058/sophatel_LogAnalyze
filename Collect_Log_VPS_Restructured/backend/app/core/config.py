import logging
import os
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

class Settings:
    DATABASE_URL: str = os.getenv("DATABASE_URL")
    SECRET_KEY: str  = os.getenv("SECRET_KEY")
    DEBUG: bool      = os.getenv("DEBUG", "false").lower() == "true"
    LOG_DIR: str     = os.getenv("LOG_DIR", "logs")
    DATA_DIR: str    = os.getenv("DATA_DIR", "data")
    # Planificateur APScheduler activé au démarrage (désactivable en test/CLI).
    SCHEDULER_ENABLED: bool = os.getenv("SCHEDULER_ENABLED", "true").lower() == "true"

    # Enrichissement des IP via API externes (RM-34) : géoloc + réputation.
    ENRICHMENT_ENABLED: bool = os.getenv("ENRICHMENT_ENABLED", "true").lower() == "true"
    # Géolocalisation (sans clé par défaut : ip-api.com). {ip} est substitué.
    GEOIP_URL: str = os.getenv("GEOIP_URL", "http://ip-api.com/json/{ip}")
    # Réputation AbuseIPDB (optionnel) : sans clé, l'étape réputation est ignorée.
    ABUSEIPDB_KEY: str = os.getenv("ABUSEIPDB_KEY", "")
    # Durée de validité du cache d'enrichissement (jours).
    ENRICHMENT_TTL_DAYS: int = int(os.getenv("ENRICHMENT_TTL_DAYS", "7"))
    # Délai d'appel HTTP externe (secondes) et plafond d'IP enrichies par requête.
    ENRICHMENT_TIMEOUT: float = float(os.getenv("ENRICHMENT_TIMEOUT", "4"))
    ENRICHMENT_MAX_PER_CALL: int = int(os.getenv("ENRICHMENT_MAX_PER_CALL", "20"))

    # Origines autorisées pour CORS (liste séparée par des virgules dans l'env)
    CORS_ORIGINS: list = [
        o.strip() for o in os.getenv(
            "CORS_ORIGINS", "http://localhost:4200,http://127.0.0.1:4200"
        ).split(",") if o.strip()
    ]

    def __init__(self):
        # Validation fail-fast, mais via exception (rattrapable par les tests /
        # Alembic / l'outillage) plutôt que sys.exit() à l'import.
        missing = []
        if not self.SECRET_KEY or self.SECRET_KEY == "changeme-secret-key":
            missing.append("SECRET_KEY (openssl rand -hex 32)")
        if not self.DATABASE_URL:
            missing.append("DATABASE_URL (postgresql://user:pass@host:5432/db)")
        if missing:
            msg = "Variables d'environnement manquantes ou invalides : " + ", ".join(missing)
            logger.error(msg)
            raise RuntimeError(msg)

settings = Settings()