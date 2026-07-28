"""
Fixtures pytest partagées (RM-27).

Principe : l'application est pointée sur une **base de test dédiée**
(`<db>_test`), créée automatiquement si absente. Le scheduler et le rate limiting
sont désactivés. Les tables sont recréées une fois, puis vidées entre chaque test.
"""
import os

# ── Environnement AVANT tout import applicatif ────────────────────────────────
# (l'engine/central config lisent DATABASE_URL/SECRET_KEY à l'import)
from sqlalchemy.engine.url import make_url  # noqa: E402

_DEV_URL = os.getenv("DATABASE_URL", "postgresql://postgres:admin123@localhost:5432/sophatel_logs")
_u = make_url(_DEV_URL)
# render_as_string(hide_password=False) : sinon str(url) masque le mot de passe en '***'.
TEST_URL = os.getenv("TEST_DATABASE_URL") or _u.set(
    database=(_u.database or "sophatel_logs") + "_test"
).render_as_string(hide_password=False)

os.environ["DATABASE_URL"] = TEST_URL
os.environ.setdefault("SECRET_KEY", "test-secret-key-0123456789abcdef0123456789abcdef")
os.environ.setdefault("ADMIN_USERNAME", "admin")
os.environ.setdefault("ADMIN_PASSWORD", "admin-test-pw")
os.environ["SCHEDULER_ENABLED"] = "false"
os.environ.setdefault("USE_MOCK", "true")

import pytest  # noqa: E402
import psycopg2  # noqa: E402
from sqlalchemy import text  # noqa: E402


def _ensure_test_database(url: str) -> None:
    """Crée la base de test si elle n'existe pas (via psycopg2, client_encoding utf8)."""
    u = make_url(url)
    conn = psycopg2.connect(
        host=u.host, port=u.port, user=u.username, password=u.password,
        dbname="postgres", client_encoding="utf8",
    )
    try:
        conn.autocommit = True
        cur = conn.cursor()
        cur.execute("SELECT 1 FROM pg_database WHERE datname = %s", (u.database,))
        if not cur.fetchone():
            cur.execute(f'CREATE DATABASE "{u.database}"')
    finally:
        conn.close()


_ensure_test_database(TEST_URL)

# ── Imports applicatifs (désormais branchés sur la base de test) ──────────────
from fastapi.testclient import TestClient  # noqa: E402
from app.core.database import Base, engine, SessionLocal  # noqa: E402
from app.core.ratelimit import limiter  # noqa: E402
from app.models import models  # noqa: E402,F401  (enregistre les tables)
from app.main import app  # noqa: E402

limiter.enabled = False  # pas de limitation de débit pendant les tests

# Tables réellement présentes (ordre enfants → parents pour le TRUNCATE CASCADE)
_TABLES = "log_entries, endpoint_stats, log_summaries, log_collections, vps_servers, users, ip_enrichment"


@pytest.fixture(scope="session", autouse=True)
def _schema():
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)


@pytest.fixture(autouse=True)
def _clean_tables():
    yield
    with engine.begin() as c:
        c.execute(text(f"TRUNCATE {_TABLES} RESTART IDENTITY CASCADE"))


@pytest.fixture
def client():
    # Le contexte déclenche le lifespan : create_all + admin par défaut,
    # scheduler désactivé (SCHEDULER_ENABLED=false).
    with TestClient(app) as c:
        yield c


def _login(client, username, password) -> str:
    r = client.post("/api/auth/login", data={"username": username, "password": password})
    assert r.status_code == 200, r.text
    return r.json()["access_token"]


@pytest.fixture
def admin_headers(client):
    token = _login(client, "admin", "admin-test-pw")
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def viewer_headers(client):
    from app.core.security import get_password_hash
    from app.models.models import User

    db = SessionLocal()
    try:
        db.add(User(
            username="viewer",
            hashed_password=get_password_hash("viewer-pw"),
            role="viewer",
        ))
        db.commit()
    finally:
        db.close()
    token = _login(client, "viewer", "viewer-pw")
    return {"Authorization": f"Bearer {token}"}
