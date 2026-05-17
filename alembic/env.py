"""
alembic/env.py — Alembic migration environment.

Key points:
- Imports Base from app.database so autogenerate can detect all models.
- Imports every model module so their tables are registered on Base.metadata
  BEFORE Alembic inspects it (models are only registered when imported).
- Reads DATABASE_URL from app.config.settings (honours .env).
- Supports both offline mode (generates SQL script) and online mode (runs on DB).

Usage:
    alembic revision --autogenerate -m "create users table"
    alembic upgrade head
    alembic downgrade -1
"""

import sys
from logging.config import fileConfig
from pathlib import Path

from alembic import context
from sqlalchemy import engine_from_config, pool

# ── Make sure the project root is on sys.path ─────────────────────────────────
# This lets Alembic find `app.*` imports when run from any directory.
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

# ── Import app config (reads .env) ────────────────────────────────────────────
from app.config import settings  # noqa: E402

# ── Import Base FIRST, then every model module ────────────────────────────────
# Alembic autogenerate works by inspecting Base.metadata.
# A model is only registered on metadata when its module is imported.
# Add a new import here every time you create a new model file.
from app.database import Base  # noqa: E402 — registers the metadata object

# Phase 0 models (always import)
from app.modules.users.user_model import Profile, User  # noqa: F401, E402

# Uncomment as you build each phase:
# from app.modules.resumes.resume_model   import Resume        # Phase 4
from app.modules.skills.skill_model     import Skill         # Phase 5 dep.
from app.modules.jobs.job_model         import Job           # Membre 2
# from app.modules.matching.recommendation_model import Recommendation
# from app.modules.skill_gap.skill_gap_model import SkillGapResult
# from app.modules.favorites.favorite_model import Favorite

# ── Alembic config object ─────────────────────────────────────────────────────
config = context.config

# Override the sqlalchemy.url from alembic.ini with the value from .env
# This is the recommended approach — a single source of truth.
config.set_main_option("sqlalchemy.url", settings.DATABASE_URL)

# Interpret the config file for Python logging
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Metadata object that Alembic will compare against the current DB schema
target_metadata = Base.metadata


# ── Offline mode — generate a SQL script without connecting ──────────────────
def run_migrations_offline() -> None:
    """
    Run migrations in 'offline' mode.

    This mode generates a SQL script that can be reviewed / applied manually.
    Useful for production environments where direct DB access is restricted.

    Run with: alembic upgrade head --sql > migration.sql
    """
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,       # detect column type changes
        compare_server_default=True,
    )
    with context.begin_transaction():
        context.run_migrations()


# ── Online mode — connect to the database and apply migrations ────────────────
def run_migrations_online() -> None:
    """
    Run migrations in 'online' mode.

    This is the standard mode used by `alembic upgrade head`.
    """
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,   # no pool needed for one-off migration runs
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            compare_type=True,
            compare_server_default=True,
        )
        with context.begin_transaction():
            context.run_migrations()


# ── Entry point ───────────────────────────────────────────────────────────────
if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()