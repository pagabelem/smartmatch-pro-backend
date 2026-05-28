# tests/conftest.py - version finale avec Phase 6 corrigée

import pytest
import time
from unittest.mock import patch
from pathlib import Path
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

# 1. Moteur SQLite
TEST_ENGINE = create_engine(
    "sqlite:///:memory:",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
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

# Patch de l'engine
import app.database as db_module

db_module.engine = TEST_ENGINE
db_module.SessionLocal = TestingSessionLocal

from app.database import Base
from app.dependencies import get_db
from app.main import app
from app.modules.users.user_model import User, Profile
from app.modules.auth.auth_model import RefreshToken
from app.modules.resumes.resume_model import Resume
from app.core.security import get_password_hash, create_access_token_with_expires


@pytest.fixture(scope="function", autouse=True)
def setup_database():
    Base.metadata.create_all(bind=TEST_ENGINE)
    yield
    Base.metadata.drop_all(bind=TEST_ENGINE)


@pytest.fixture
def db_session():
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.rollback()
        session.close()


@pytest.fixture
def client(db_session):
    def _override_get_db():
        try:
            yield db_session
        finally:
            pass

    app.dependency_overrides[get_db] = _override_get_db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


@pytest.fixture(autouse=True)
def mock_db_check():
    with patch("app.main.check_db_connection", return_value=True):
        yield


@pytest.fixture
def auth_headers(client) -> dict:
    email = f"test_{int(time.time()*1000)}@example.com"
    r = client.post("/api/v1/auth/register", json={"email": email, "password": "Test123!@#"})
    assert r.status_code == 201
    token = r.json()["data"]["access_token"]
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def admin_auth_headers(client) -> dict:
    email = f"admin_{int(time.time()*1000)}@example.com"
    r = client.post("/api/v1/auth/register", json={"email": email, "password": "Admin123!@#"})
    assert r.status_code == 201

    from app.database import SessionLocal

    db = SessionLocal()
    try:
        user = db.query(User).filter(User.email == email).first()
        if user:
            user.is_superuser = True
            db.commit()
    finally:
        db.close()

    token = r.json()["data"]["access_token"]
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def test_user(db_session) -> User:
    user = User(
        email="testuser@example.com",
        hashed_password=get_password_hash("Test123!@#"),
        is_superuser=False,
        is_active=True,
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


@pytest.fixture
def test_admin(db_session) -> User:
    admin = User(
        email="admin@example.com",
        hashed_password=get_password_hash("Admin123!@#"),
        is_superuser=True,
        is_active=True,
    )
    db_session.add(admin)
    db_session.commit()
    db_session.refresh(admin)
    return admin


@pytest.fixture
def test_second_user(db_session) -> User:
    user = User(
        email="seconduser@example.com",
        hashed_password=get_password_hash("Test123!@#"),
        is_superuser=False,
        is_active=True,
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


@pytest.fixture
def test_profile(db_session, test_user) -> Profile:
    profile = Profile(
        user_id=test_user.id,
        first_name="Test",
        last_name="User",
        bio="Software Engineer",
        location="Casablanca",
        skills_raw=["python", "fastapi"],
        skills_extracted=["python", "fastapi"],
    )
    db_session.add(profile)
    db_session.commit()
    db_session.refresh(profile)
    return profile


@pytest.fixture
def test_second_profile(db_session, test_second_user) -> Profile:
    profile = Profile(
        user_id=test_second_user.id,
        first_name="Second",
        last_name="User",
        bio="Data Scientist",
        location="Rabat",
        skills_raw=["sql", "pandas"],
        skills_extracted=["sql", "pandas"],
    )
    db_session.add(profile)
    db_session.commit()
    db_session.refresh(profile)
    return profile


@pytest.fixture
def user_token(test_user) -> str:
    return create_access_token_with_expires(data={"sub": str(test_user.id)})


@pytest.fixture
def second_user_token(test_second_user) -> str:
    return create_access_token_with_expires(data={"sub": str(test_second_user.id)})


@pytest.fixture
def admin_token(test_admin) -> str:
    return create_access_token_with_expires(data={"sub": str(test_admin.id)})


# ---------------------------------------------------------------------------
# Phase 4 - Resume fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def test_resume(db_session, test_profile) -> Resume:
    resume = Resume(
        profile_id=test_profile.id,
        filename="test_cv.pdf",
        file_path=f"resumes/{test_profile.id}/test_cv.pdf",
        file_size=1024,
        mime_type="application/pdf",
        raw_text="This is a test CV content with Python and FastAPI skills.",
        is_parsed=False,
    )
    db_session.add(resume)
    db_session.commit()
    db_session.refresh(resume)
    return resume


# ---------------------------------------------------------------------------
# Phase 6 - Storage fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def temp_storage_dir(tmp_path) -> Path:
    storage_dir = tmp_path / "storage"
    storage_dir.mkdir(parents=True, exist_ok=True)
    return storage_dir


@pytest.fixture
def mock_storage_service(temp_storage_dir):
    from app.modules.storage.storage_service import StorageService

    service = StorageService(
        base_dir=temp_storage_dir,
        allowed_extensions={".pdf", ".docx", ".png", ".jpg", ".jpeg"},
        max_size=5 * 1024 * 1024,
    )
    return service


@pytest.fixture
def test_file_path(temp_storage_dir, test_profile) -> Path:
    subfolder = temp_storage_dir / "resumes" / str(test_profile.id)
    subfolder.mkdir(parents=True, exist_ok=True)
    file_path = subfolder / "test_cv.pdf"
    file_path.write_bytes(b"%PDF-1.4 test content")
    return file_path
