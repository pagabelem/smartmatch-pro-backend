# tests/conftest.py

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from fastapi.testclient import TestClient

from app.database import Base
from app.main import app
from app.dependencies import get_db

# PostgreSQL de test — même base que le dev
SQLALCHEMY_TEST_URL = "postgresql+psycopg2://postgres:admin@localhost:5432/db_pro_test"

engine = create_engine(SQLALCHEMY_TEST_URL)

TestingSessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine,
)


def override_get_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


@pytest.fixture(scope="function", autouse=True)
def setup_database():
    """Crée toutes les tables avant chaque test et les supprime après."""
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)


@pytest.fixture(scope="function")
def db():
    """Session de base de données pour les tests."""
    database = TestingSessionLocal()
    try:
        yield database
    finally:
        database.close()


@pytest.fixture(scope="function")
def client():
    """Client HTTP de test FastAPI."""
    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()