# tests/conftest.py
"""
conftest.py — Shared pytest fixtures for all test phases.

Architecture
------------
- Un seul moteur SQLite en mémoire partagé par tous les fichiers de tests.
- reset_tables (autouse) recrée les tables avant chaque test.
- db et client sont disponibles pour test_phase0, test_phase1, etc.
- get_db est overridé globalement → les routes HTTP utilisent SQLite, pas PostgreSQL.
"""

from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker

from app.database import Base
from app.dependencies import get_db
from app.main import app

# ── Moteur SQLite partagé ─────────────────────────────────────────────────────
TEST_ENGINE = create_engine(
    "sqlite:///:memory:",
    connect_args={"check_same_thread": False},
)

# FK enforcement sur SQLite (désactivé par défaut)
@event.listens_for(TEST_ENGINE, "connect")
def _set_sqlite_pragma(dbapi_connection, _):
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.close()

TestingSessionLocal = sessionmaker(
    bind=TEST_ENGINE,
    autocommit=False,
    autoflush=False,
    expire_on_commit=False,
)


# ── Fixtures autouse ──────────────────────────────────────────────────────────
@pytest.fixture(autouse=True)
def override_db_check():
    """Empêche le lifespan de crasher en l'absence de PostgreSQL."""
    with patch("app.main.check_db_connection", return_value=True):
        yield


@pytest.fixture(autouse=True)
def reset_tables():
    """Recrée toutes les tables avant chaque test, les supprime après."""
    Base.metadata.create_all(bind=TEST_ENGINE)
    yield
    Base.metadata.drop_all(bind=TEST_ENGINE)


# ── Fixtures partagées ────────────────────────────────────────────────────────
@pytest.fixture
def db():
    """Session SQLite injectée dans les tests ORM."""
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture
def client(db):
    """
    TestClient avec get_db overridé vers SQLite.
    La MÊME session que db est injectée dans les routes HTTP.
    """
    def _override():
        yield db

    app.dependency_overrides[get_db] = _override
    with TestClient(app, raise_server_exceptions=True) as c:
        yield c
    app.dependency_overrides.clear()