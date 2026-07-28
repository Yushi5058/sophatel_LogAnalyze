# Image du backend Sophatel (FastAPI + Uvicorn) — RM-28
# Python 3.12 pour rester aligné avec le projet (cf. .python-version).
FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

# psycopg2-binary embarque libpq ; cryptography / pandas ont des wheels manylinux
# -> aucun outil de compilation nécessaire, l'image slim suffit.
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Code applicatif (exclusions dans .dockerignore : .env, .venv, logs, tests...)
COPY . .

EXPOSE 8000

# Applique les migrations puis démarre l'API.
# Le service `db` est attendu via depends_on: condition: service_healthy
# dans docker-compose.yml (la base accepte les connexions avant ce lancement).
CMD ["sh", "-c", "alembic upgrade head && exec uvicorn app.main:app --host 0.0.0.0 --port 8000"]
