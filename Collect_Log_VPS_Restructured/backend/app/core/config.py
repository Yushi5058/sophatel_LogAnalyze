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