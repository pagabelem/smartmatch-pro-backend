"""
conftest.py — Fixtures partagées Phase 7.
"""

import io
import asyncio
import time
import itertools
from pathlib import Path
from typing import AsyncGenerator
from unittest.mock import patch, MagicMock

import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from sqlalchemy import select
from sqlalchemy.pool import StaticPool
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

_conftest_counter = itertools.count(1)

async_test_engine = create_async_engine(
    "sqlite+aiosqlite:///:memory:",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)

AsyncTestSessionLocal = async_sessionmaker(
    bind=async_test_engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False,
    autocommit=False,
)


async def _override_get_db():
    async with AsyncTestSessionLocal() as session:
        yield session


def _make_mock_nlp():
    mock_doc = MagicMock()
    mock_doc.ents = []
    mock_doc.__iter__ = MagicMock(return_value=iter([]))
    mock_nlp = MagicMock()
    mock_nlp.return_value = mock_doc
    return mock_nlp


@pytest.fixture(scope="session")
def event_loop():
    loop = asyncio.get_event_loop_policy().new_event_loop()
    asyncio.set_event_loop(loop)
    yield loop
    loop.close()


@pytest_asyncio.fixture(scope="function", autouse=True)
async def setup_database():
    from app.database import Base
    import app.modules.auth.auth_model       # noqa: F401
    import app.modules.users.user_model      # noqa: F401
    import app.modules.skills.skill_model    # noqa: F401
    import app.modules.resumes.resume_model  # noqa: F401

    async with async_test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with async_test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest_asyncio.fixture
async def async_client() -> AsyncGenerator[AsyncClient, None]:
    from app.main import app
    from app.database import get_db

    app.dependency_overrides[get_db] = _override_get_db
    with patch("app.modules.nlp.skill_extractor._nlp", new=_make_mock_nlp()):
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://testserver",
        ) as ac:
            yield ac
    app.dependency_overrides.clear()


@pytest.fixture
def sync_client():
    from app.main import app
    from app.database import get_db
    from fastapi.testclient import TestClient

    app.dependency_overrides[get_db] = _override_get_db
    with patch("app.modules.nlp.skill_extractor._nlp", new=_make_mock_nlp()):
        with TestClient(app, raise_server_exceptions=True) as c:
            yield c
    app.dependency_overrides.clear()


# ===========================================================================
# FIXTURE LEGACY — client (TestClient) utilise aiosqlite comme async_client
# ===========================================================================

@pytest.fixture(scope="function")
def client():
    """
    TestClient synchrone qui utilise la MEME base aiosqlite que les tests async.
    Évite les conflits de thread SQLite en utilisant aiosqlite partout.
    """
    from app.main import app
    from app.database import get_db
    from fastapi.testclient import TestClient

    # Utilise la fonction async existante (comme async_client et sync_client)
    app.dependency_overrides[get_db] = _override_get_db
    
    try:
        with TestClient(app, raise_server_exceptions=True) as test_client:
            yield test_client
    finally:
        app.dependency_overrides.pop(get_db, None)


# ===========================================================================
# FIXTURE LEGACY — db (session SQLAlchemy SYNCHRONE pour ORM direct)
# ===========================================================================

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

@pytest.fixture(scope="function")
def db():
    """
    Session DB SQLite sync pour les tests legacy qui accèdent directement à l'ORM.
    ATTENTION: Cette session est INDÉPENDANTE de la base utilisée par l'API.
    """
    engine = create_engine("sqlite:///:memory:", echo=False, future=True)
    from app.database import Base
    Base.metadata.create_all(engine)
    SessionLocal = sessionmaker(bind=engine, expire_on_commit=False)
    session = SessionLocal()
    
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(engine)
        engine.dispose()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

async def _register_and_login_async(client, email, password, full_name, is_superuser=False) -> dict:
    prefix, domain = email.split("@")
    unique = f"{prefix}_{int(time.time()*1000000)}_{next(_conftest_counter)}@{domain}"

    r = await client.post("/api/v1/auth/register", json={
        "email": unique, "password": password,
        "first_name": full_name.split()[0],
        "last_name": full_name.split()[1] if len(full_name.split()) > 1 else "User",
    })
    assert r.status_code in (200, 201), f"Register failed: {r.text}"

    lr = await client.post("/api/v1/auth/login", json={"email": unique, "password": password})
    assert lr.status_code == 200, f"Login failed: {lr.text}"

    ld = lr.json()
    target = ld.get("data", ld)
    token = target["access_token"]
    refresh_tok = target.get("refresh_token", "")
    user_data = target.get("user", target)

    if is_superuser:
        from app.modules.users.user_model import User
        async with AsyncTestSessionLocal() as db:
            res = await db.execute(select(User).where(User.email == unique))
            u = res.scalar_one_or_none()
            if u:
                u.is_superuser = True
                await db.commit()
                user_data["is_superuser"] = True

    return {
        "id": user_data.get("id"),
        "email": unique,
        "token": token,
        "refresh_token": refresh_tok,
        "headers": {"Authorization": f"Bearer {token}"},
        "user": user_data,
        "data": user_data,
    }


def _register_and_login_sync(client, email, password, full_name, is_superuser=False) -> dict:
    prefix, domain = email.split("@")
    unique = f"{prefix}_{int(time.time()*1000000)}_{next(_conftest_counter)}@{domain}"

    r = client.post("/api/v1/auth/register", json={
        "email": unique, "password": password,
        "first_name": full_name.split()[0],
        "last_name": full_name.split()[1] if len(full_name.split()) > 1 else "User",
    })
    assert r.status_code in (200, 201), f"Register failed: {r.text}"

    lr = client.post("/api/v1/auth/login", json={"email": unique, "password": password})
    assert lr.status_code == 200, f"Login failed: {lr.text}"

    ld = lr.json()
    target = ld.get("data", ld)
    token = target["access_token"]
    refresh_tok = target.get("refresh_token", "")
    user_data = target.get("user", target)

    return {
        "id": user_data.get("id"),
        "email": unique,
        "token": token,
        "refresh_token": refresh_tok,
        "headers": {"Authorization": f"Bearer {token}"},
        "user": user_data,
        "data": user_data,
    }


# ---------------------------------------------------------------------------
# Fixtures utilisateurs async
# ---------------------------------------------------------------------------

@pytest_asyncio.fixture
async def test_user(async_client) -> dict:
    return await _register_and_login_async(async_client, "user@test.com", "Test123!@#", "Standard User")


@pytest_asyncio.fixture
async def test_admin(async_client) -> dict:
    return await _register_and_login_async(
        async_client, "admin@test.com", "AdminPass123!", "Admin User", is_superuser=True
    )


@pytest_asyncio.fixture
async def test_second_user(async_client) -> dict:
    return await _register_and_login_async(async_client, "second@test.com", "SecurePass123!", "Second User")


# ---------------------------------------------------------------------------
# Fixtures utilisateurs sync
# ---------------------------------------------------------------------------

@pytest.fixture
def auth_headers(sync_client) -> dict:
    data = _register_and_login_sync(sync_client, "user@example.com", "Test123!@#", "Test User")
    return data["headers"]


@pytest.fixture
def admin_auth_headers(sync_client) -> dict:
    data = _register_and_login_sync(sync_client, "admin@example.com", "Admin123!@#", "Admin User")
    import asyncio as _aio
    from app.modules.users.user_model import User

    async def _promote():
        async with AsyncTestSessionLocal() as db:
            res = await db.execute(select(User).where(User.email == data["email"]))
            u = res.scalar_one_or_none()
            if u:
                u.is_superuser = True
                await db.commit()

    try:
        loop = _aio.get_event_loop()
        if loop.is_running():
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor() as pool:
                pool.submit(_aio.run, _promote()).result()
        else:
            loop.run_until_complete(_promote())
    except Exception:
        pass

    return data["headers"]


@pytest.fixture
def user_token(sync_client) -> str:
    data = _register_and_login_sync(sync_client, "token@example.com", "Test123!@#", "Token User")
    return data["token"]


@pytest.fixture
def refresh_token(sync_client) -> str:
    data = _register_and_login_sync(sync_client, "refresh@example.com", "Test123!@#", "Refresh User")
    return data.get("refresh_token", "")


# ---------------------------------------------------------------------------
# Fixtures profils
# ---------------------------------------------------------------------------

async def _create_or_get_profile(client, user, full_name="Test User"):
    resp = await client.post(
        "/api/v1/profiles/",
        json={
            "full_name": full_name,
            "title": "Dev Python",
            "bio": "Backend",
            "location": "Paris",
            "experience_years": 3,
            "education_level": "master",
        },
        headers=user["headers"],
    )
    if resp.status_code in (200, 201):
        data = resp.json()
        return data.get("data", data)
    if resp.status_code == 409:
        me_resp = await client.get("/api/v1/profiles/me", headers=user["headers"])
        if me_resp.status_code == 200:
            data = me_resp.json()
            return data.get("data", data)
    raise AssertionError(f"Profile failed: {resp.text}")


@pytest_asyncio.fixture
async def test_profile(async_client, test_user):
    return await _create_or_get_profile(async_client, test_user, "Standard User")


@pytest_asyncio.fixture
async def test_second_profile(async_client, test_second_user):
    return await _create_or_get_profile(async_client, test_second_user, "Second User")


# ---------------------------------------------------------------------------
# Fixtures CV
# ---------------------------------------------------------------------------

@pytest_asyncio.fixture
async def test_resume(async_client, test_user, test_profile):
    fake_pdf = io.BytesIO(b"%PDF-1.4 fake pdf content for testing")
    resp = await async_client.post(
        "/api/v1/resumes/upload",
        files={"file": ("cv_test.pdf", fake_pdf, "application/pdf")},
        headers=test_user["headers"],
    )
    assert resp.status_code in (200, 201), f"Resume upload failed: {resp.text}"
    data = resp.json()
    return data.get("data", data)


# ---------------------------------------------------------------------------
# Fixtures storage / NLP
# ---------------------------------------------------------------------------

@pytest.fixture
def temp_storage_dir(tmp_path) -> Path:
    d = tmp_path / "storage"
    d.mkdir(parents=True, exist_ok=True)
    return d


@pytest.fixture
def mock_storage_service(temp_storage_dir):
    from app.modules.storage.storage_service import StorageService
    return StorageService(
        base_dir=temp_storage_dir,
        allowed_extensions={".pdf", ".docx", ".png"},
        max_size=5 * 1024 * 1024,
    )


@pytest.fixture
def mock_nlp_extraction():
    with patch(
        "app.modules.nlp.skill_extractor.extract_skills_from_text",
        return_value=["python", "fastapi", "postgresql", "docker", "git"],
    ) as m:
        yield m


@pytest.fixture
def mock_nlp_service():
    with patch("app.modules.nlp.nlp_router.process_resume") as mp, \
         patch("app.modules.nlp.nlp_router.bulk_process_resumes") as mb, \
         patch("app.modules.nlp.nlp_router.get_nlp_status") as ms, \
         patch("app.modules.nlp.nlp_router.get_profile_skills") as msk, \
         patch("app.modules.nlp.nlp_router.extract_text_debug") as md:

        mp.return_value = {"resume_id": 1, "skills_extracted": ["python"], "processing_time_ms": 42, "status": "success", "message": None}
        mb.return_value = {"profile_id": 1, "processed": 2, "skipped": 0, "total_skills": 5, "processing_time_ms": 120, "status": "success"}
        ms.return_value = {"resume_id": 1, "is_parsed": True, "processed_at": None, "raw_text_length": 1500}
        msk.return_value = {"profile_id": 1, "skills": ["python", "fastapi"], "total": 2}
        md.return_value = ["python", "docker"]

        yield {"process": mp, "bulk": mb, "status": ms, "skills": msk, "debug": md}