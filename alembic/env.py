"""
alembic/env.py — Alembic migration environment.
"""

import sys
from logging.config import fileConfig
from pathlib import Path

from alembic import context
from sqlalchemy import engine_from_config, pool

# ── Make sure the project root is on sys.path ─────────────────────────────────
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

# ── Import app config (reads .env) ────────────────────────────────────────────
from app.config import settings  # noqa: E402

# ── Import Base FIRST, then every model module ────────────────────────────────
from app.database import Base  # noqa: E402

# Membre 1 models
from app.modules.users.user_model import Profile, User  # noqa: F401, E402
from app.modules.auth.auth_model import RefreshToken    # noqa: F401, E402
from app.modules.resumes.resume_model import Resume     # noqa: F401, E402
from app.modules.skills.skill_model import Skill        # noqa: F401, E402

# ✅ Membre 2 models
from app.modules.jobs.job_model import Job              # noqa: F401, E402
from app.modules.imports.import_model import Import     # noqa: F401, E402

# ── Alembic config object ─────────────────────────────────────────────────────
config = context.config
config.set_main_option("sqlalchemy.url", settings.DATABASE_URL)

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def run_migrations_offline() -> None:
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
        compare_server_default=True,
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
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


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()