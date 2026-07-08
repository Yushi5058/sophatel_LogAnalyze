from contextlib import asynccontextmanager
import logging

from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from app.routers import logs, stats, vps
from app.routers import collect_router, analyze_router
from app.routers import endpoint_stats_router
from app.routers import auth_router
from app.core.database import engine, Base, get_db
from app.core.scheduler import scheduler, register_jobs
from app.core.security import get_current_user
from app.core.config import settings
from app.core.ratelimit import limiter
from slowapi.errors import RateLimitExceeded
from slowapi import _rate_limit_exceeded_handler

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(name)s — %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)


def create_default_users():
    """
    Crée le compte admin initial si la table est vide.
    Le mot de passe n'est PAS en dur : il vient de ADMIN_PASSWORD (.env), sinon
    un mot de passe aléatoire est généré et journalisé une seule fois.
    """
    import os
    import secrets
    from sqlalchemy.orm import Session
    from app.models.models import User
    from app.core.security import get_password_hash

    log = logging.getLogger(__name__)
    db: Session = next(get_db())
    try:
        if db.query(User).count() == 0:
            username = os.getenv("ADMIN_USERNAME", "admin")
            password = os.getenv("ADMIN_PASSWORD")
            generated = not password
            if generated:
                password = secrets.token_urlsafe(16)

            db.add(User(
                username=username,
                hashed_password=get_password_hash(password),
                full_name="Administrateur",
                role="admin",
            ))
            db.commit()

            if generated:
                log.warning(
                    "Compte admin '%s' créé avec un mot de passe ALÉATOIRE : %s\n"
                    "  → Notez-le et changez-le. Définissez ADMIN_PASSWORD dans .env "
                    "pour choisir ce mot de passe.",
                    username, password,
                )
            else:
                log.info("Compte admin '%s' créé depuis ADMIN_PASSWORD.", username)
    finally:
        db.close()


@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(bind=engine)
    create_default_users()
    register_jobs()
    scheduler.start()
    yield
    scheduler.shutdown()


app = FastAPI(
    title="Sophatel - VPS Log API",
    description="API de collecte et analyse des logs Nginx",
    version="1.0.0",
    lifespan=lifespan,
)

# Limitation de débit (anti brute-force) — renvoie 429 au-delà du seuil
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,                       # configurable via CORS_ORIGINS
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"], # méthodes réellement utilisées
    allow_headers=["Authorization", "Content-Type"],           # en-têtes réellement utilisés
)

# Route d'authentification — SANS protection JWT
app.include_router(auth_router.router, prefix="/api/auth", tags=["Auth"])

# Toutes les autres routes — PROTÉGÉES par JWT
_auth = {"dependencies": [Depends(get_current_user)]}

app.include_router(logs.router,                    prefix="/api/logs",           tags=["Logs"],           **_auth)
app.include_router(stats.router,                   prefix="/api/stats",          tags=["Stats"],          **_auth)
app.include_router(vps.router,                     prefix="/api/vps",            tags=["VPS"],            **_auth)
app.include_router(collect_router.router,          prefix="/api/collect",        tags=["Collect"],        **_auth)
app.include_router(analyze_router.router,          prefix="/api/analyze",        tags=["Analyze"],        **_auth)
app.include_router(endpoint_stats_router.router,   prefix="/api/endpoint-stats", tags=["Endpoint Stats"], **_auth)


@app.get("/api/auth/me", tags=["Auth"])
def get_me(current_user=Depends(get_current_user)):
    return {
        "username": current_user.username,
        "full_name": current_user.full_name,
        "role": current_user.role,
    }


@app.get("/api/scheduler/jobs", tags=["Scheduler"])
def list_jobs(current_user=Depends(get_current_user)):
    return [
        {"id": job.id, "name": job.name, "next_run": str(job.next_run_time)}
        for job in scheduler.get_jobs()
    ]


@app.get("/")
def root():
    return {"status": "ok", "service": "Sophatel VPS Log API"}


@app.get("/health")
def health():
    return {"status": "healthy"}
