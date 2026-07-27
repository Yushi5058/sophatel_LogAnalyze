from logging.config import fileConfig
from sqlalchemy import engine_from_config, pool
from alembic import context
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.core.database import Base
from app.models import models  # noqa: F401 — importe tous les modèles

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Surcharge l'URL depuis .env si disponible
# La seul fois ou on a editer manuellement ce fichier pour lire le db url et importer metadata
db_url = os.getenv("DATABASE_URL")
if db_url:
    config.set_main_option("sqlalchemy.url", db_url)

target_metadata = Base.metadata

# Tables gérées HORS Alembic (créées/maintenues par des libs tierces).
# `apscheduler_jobs` est créée par APScheduler (RM-26) : on l'exclut de
# l'autogénération pour éviter un faux drift (proposition de DROP).
_IGNORED_TABLES = {"apscheduler_jobs"}


def include_name(name, type_, parent_names):
    if type_ == "table" and name in _IGNORED_TABLES:
        return False
    return True


def run_migrations_offline():
    url = config.get_main_option("sqlalchemy.url")
    context.configure(url=url, target_metadata=target_metadata,
                      literal_binds=True, dialect_opts={"paramstyle": "named"},
                      include_name=include_name)
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online():
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    with connectable.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata,
                          include_name=include_name)
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
