"""
database.py — SQLAlchemy engine, session factory, and declarative Base.
"""

from sqlalchemy import create_engine, text
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from app.config import settings


# ── Sync Engine (for migrations, scripts, and health checks) ─────────────────
sync_engine = create_engine(
    settings.DATABASE_URL,
    echo=settings.DEBUG,
    pool_size=settings.DB_POOL_SIZE,
    max_overflow=settings.DB_MAX_OVERFLOW,
    pool_timeout=settings.DB_POOL_TIMEOUT,
    pool_recycle=settings.DB_POOL_RECYCLE,
    pool_pre_ping=True,
)


# ── Async Engine (for FastAPI async routes) ──────────────────────────────────
# Construire l'URL async correctement
if "postgresql+asyncpg" in settings.DATABASE_URL:
    async_database_url = settings.DATABASE_URL
elif "postgresql+psycopg2" in settings.DATABASE_URL:
    async_database_url = settings.DATABASE_URL.replace(
        "postgresql+psycopg2://", "postgresql+asyncpg://"
    )
elif "postgresql://" in settings.DATABASE_URL:
    async_database_url = settings.DATABASE_URL.replace(
        "postgresql://", "postgresql+asyncpg://"
    )
else:
    async_database_url = f"postgresql+asyncpg://{settings.DATABASE_URL.split('://')[1]}"

async_engine = create_async_engine(
    async_database_url,
    echo=settings.DEBUG,
    pool_size=settings.DB_POOL_SIZE,
    max_overflow=settings.DB_MAX_OVERFLOW,
    pool_timeout=settings.DB_POOL_TIMEOUT,
    pool_recycle=settings.DB_POOL_RECYCLE,
    pool_pre_ping=True,
)


# ── Async Session factory ────────────────────────────────────────────────────
AsyncSessionLocal = async_sessionmaker(
    async_engine,
    class_=AsyncSession,
    autocommit=False,
    autoflush=False,
    expire_on_commit=False,
)


# ── Sync Session factory ─────────────────────────────────────────────────────
SessionLocal = sessionmaker(
    bind=sync_engine,
    autocommit=False,
    autoflush=False,
    expire_on_commit=False,
)


# ── Dependency for FastAPI routes ────────────────────────────────────────────
async def get_db() -> AsyncSession:
    """
    FastAPI dependency that provides an async database session.
    Usage: db: AsyncSession = Depends(get_db)
    """
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


# ── Declarative Base ─────────────────────────────────────────────────────────
class Base(DeclarativeBase):
    """
    All SQLAlchemy models must inherit from this Base.
    """
    pass


# ── Utility functions ────────────────────────────────────────────────────────
def create_all_tables() -> None:
    """Create all tables registered on Base.metadata."""
    Base.metadata.create_all(bind=sync_engine)


def drop_all_tables() -> None:
    """Drop all tables."""
    Base.metadata.drop_all(bind=sync_engine)


def check_db_connection() -> bool:
    """Return True if PostgreSQL is reachable, False otherwise."""
    try:
        with sync_engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        return True
    except Exception:
        return False


async def check_db_connection_async() -> bool:
    """Async version of check_db_connection for async contexts."""
    try:
        async with async_engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        return True
    except Exception:
        return False