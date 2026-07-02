import os
from dotenv import load_dotenv

load_dotenv()

class Settings:
    DATABASE_URL: str = os.getenv("DATABASE_URL")
    SECRET_KEY: str  = os.getenv("SECRET_KEY", "changeme-secret-key")
    DEBUG: bool      = os.getenv("DEBUG", "false").lower() == "true"
    LOG_DIR: str     = os.getenv("LOG_DIR", "logs")
    DATA_DIR: str    = os.getenv("DATA_DIR", "data")

settings = Settings()
print("DATABASE_URL =", os.getenv("DATABASE_URL"))