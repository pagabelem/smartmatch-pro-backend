"""
database.py — SQLAlchemy engine, session factory, and declarative Base.

PostgreSQL-specific notes
--------------------------
- Uses psycopg2 as the sync driver (install: pip install psycopg2-binary).
- QueuePool is the default pool for PostgreSQL (unlike SQLite which uses NullPool).
- Pool settings (size, overflow, recycle) come from app.config.settings.
- PRAGMA foreign_keys is NOT needed — PostgreSQL enforces FK constraints natively.
- JSON columns map to native PostgreSQL JSON/JSONB (faster than TEXT on SQLite).

Usage
-----
  from app.database import Base, SessionLocal, engine
"""

from sqlalchemy import create_engine, text
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from app.config import settings


# ── Engine ────────────────────────────────────────────────────────────────────
engine = create_engine(
    settings.DATABASE_URL,
    echo=settings.DEBUG,               # log all SQL statements when DEBUG=True
    pool_size=settings.DB_POOL_SIZE,
    max_overflow=settings.DB_MAX_OVERFLOW,
    pool_timeout=settings.DB_POOL_TIMEOUT,
    pool_recycle=settings.DB_POOL_RECYCLE,
    pool_pre_ping=True,                # test connections before using them
                                       # (detects stale connections after DB restart)
)
# pool_pre_ping explanation:
#   PostgreSQL closes idle connections after a configurable timeout (default 10 min).
#   Without pre_ping, SQLAlchemy would try to reuse a dead connection and raise an error.
#   With pre_ping=True it sends a lightweight "SELECT 1" before each checkout — if the
#   connection is dead it transparently opens a new one. Tiny overhead, huge reliability gain.


# ── Session factory ───────────────────────────────────────────────────────────
SessionLocal = sessionmaker(
    bind=engine,
    autocommit=False,        # explicit db.commit() required
    autoflush=False,         # prevent implicit flushes that can mask bugs
    expire_on_commit=False,  # keep objects usable after commit without re-querying
)


# ── Declarative Base ──────────────────────────────────────────────────────────
class Base(DeclarativeBase):
    """
    All SQLAlchemy models must inherit from this Base.

    Example:
        from app.database import Base

        class User(Base):
            __tablename__ = "users"
            ...
    """
    pass


# ── Utility functions ─────────────────────────────────────────────────────────
def create_all_tables() -> None:
    """
    Create all tables registered on Base.metadata.
    Prefer Alembic migrations in production. Use this only in tests.
    """
    Base.metadata.create_all(bind=engine)


def drop_all_tables() -> None:
    """Drop all tables. Use only in tests or the reset_db.py script."""
    Base.metadata.drop_all(bind=engine)


def check_db_connection() -> bool:
    """
    Return True if PostgreSQL is reachable, False otherwise.
    Used by the /health endpoint and the lifespan startup hook.
    """
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        return True
    except Exception:
        return False