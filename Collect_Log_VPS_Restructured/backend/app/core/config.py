import logging
import os
import sys
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
        if not self.SECRET_KEY or self.SECRET_KEY == "changeme-secret-key":
            logger.error(
                "SECRET_KEY non définie ou valeur par défaut. "
                "Générez-en une avec : openssl rand -hex 32"
            )
            sys.exit(1)

settings = Settings()