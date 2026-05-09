import pytest
from unittest.mock import patch
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

# 1. Moteur SQLite avec StaticPool (CRITIQUE pour le multi-threading FastAPI)
TEST_ENGINE = create_engine(
    "sqlite:///:memory:",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool, # Garde la connexion ouverte pour tout le thread de test
)

@event.listens_for(TEST_ENGINE, "connect")
def _fk_pragma(dbapi_conn, _):
    cur = dbapi_conn.cursor()
    cur.execute("PRAGMA foreign_keys=ON")
    cur.close()

TestingSessionLocal = sessionmaker(
    bind=TEST_ENGINE,
    autocommit=False,
    autoflush=False,
    expire_on_commit=False,
)

# 2. Patch de l'engine AVANT les imports de l'app
import app.database as db_module
db_module.engine = TEST_ENGINE
db_module.SessionLocal = TestingSessionLocal

# 3. Import des composants et FORCER le chargement des modèles
from app.database import Base
from app.dependencies import get_db
from app.main import app

# On importe explicitement tous les modèles pour que Base.metadata les enregistre
from app.modules.users.user_model import User, Profile
from app.modules.auth.auth_model import RefreshToken
from app.modules.skills.skill_model import Skill

@pytest.fixture(scope="function", autouse=True)
def setup_database():
    """Crée proprement les tables et gère le cycle de vie."""
    # Debug pour vérifier que les modèles sont chargés
    # print(f"Tables à créer : {Base.metadata.tables.keys()}") 
    
    Base.metadata.create_all(bind=TEST_ENGINE)
    yield
    Base.metadata.drop_all(bind=TEST_ENGINE)

@pytest.fixture
def db():
    """Session isolée pour chaque test."""
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()

@pytest.fixture
def client(db):
    """Client avec injection de la session de test."""
    def _override_get_db():
        try:
            yield db
        finally:
            pass

    app.dependency_overrides[get_db] = _override_get_db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()

@pytest.fixture(autouse=True)
def mock_db_check():
    """Évite le crash au démarrage si Postgres n'est pas là."""
    with patch("app.main.check_db_connection", return_value=True):
        yield