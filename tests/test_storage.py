"""
Tests Phase 7 — Module NLP
Couvre :
- Unitaires : clean_text, extract_skills_from_text (avec mocks spaCy)
- Intégration : routes process, bulk, status, skills, extract-text
- Permissions : propriétaire vs autre user vs admin
"""

import time
import itertools
import pytest
from unittest.mock import patch, MagicMock
from httpx import AsyncClient


_nlp_counter = itertools.count(500)


# ---------------------------------------------------------------------------
# Helpers locaux (emails uniques garantis)
# ---------------------------------------------------------------------------

async def create_test_user(async_client: AsyncClient, is_superuser: bool = False) -> dict:
    unique = f"nlp_{int(time.time()*1000)}_{next(_nlp_counter)}@example.com"
    password = "Test123!@#"

    r = await async_client.post("/api/v1/auth/register", json={
        "email": unique, "password": password,
        "first_name": "NLP", "last_name": "User",
    })
    assert r.status_code in (200, 201), f"Register failed: {r.text}"

    lr = await async_client.post("/api/v1/auth/login", json={
        "email": unique, "password": password,
    })
    assert lr.status_code == 200, f"Login failed: {lr.text}"

    data = lr.json().get("data", lr.json())
    token = data["access_token"]
    user_data = data.get("user", data)

    if is_superuser:
        from sqlalchemy import select
        from tests.conftest import AsyncTestSessionLocal
        from app.modules.users.user_model import User
        async with AsyncTestSessionLocal() as db:
            res = await db.execute(select(User).where(User.email == unique))
            u = res.scalar_one_or_none()
            if u:
                u.is_superuser = True
                await db.commit()

    return {
        "id": user_data.get("id"),
        "email": unique,
        "token": token,
        "headers": {"Authorization": f"Bearer {token}"},
    }


async def create_test_profile(async_client: AsyncClient, headers: dict) -> dict:
    resp = await async_client.post("/api/v1/profiles/", json={
        "full_name": "NLP Test User",
        "title": "Developer",
        "bio": "test",
        "location": "Paris",
        "experience_years": 2,
        "education_level": "master",
    }, headers=headers)

    if resp.status_code == 409:
        me = await async_client.get("/api/v1/profiles/me", headers=headers)
        if me.status_code == 200:
            d = me.json()
            return d.get("data", d)

    assert resp.status_code in (200, 201), f"Profile failed: {resp.text}"
    d = resp.json()
    return d.get("data", d)


async def create_test_resume(async_client: AsyncClient, headers: dict) -> dict:
    import io
    fake_pdf = io.BytesIO(b"%PDF-1.4 Python FastAPI developer")
    resp = await async_client.post(
        "/api/v1/resumes/upload",
        files={"file": ("cv.pdf", fake_pdf, "application/pdf")},
        headers=headers,
    )
    assert resp.status_code in (200, 201), f"Resume upload failed: {resp.text}"
    d = resp.json()
    return d.get("data", d)


# ===========================================================================
# Tests unitaires — text_cleaner.py
# ===========================================================================

class TestCleanText:
    def test_removes_html_tags(self):
        from app.modules.nlp.text_cleaner import remove_html_tags
        result = remove_html_tags("<p>Hello <b>World</b></p>")
        assert "<" not in result
        assert "Hello" in result
        assert "World" in result

    def test_decodes_html_entities(self):
        from app.modules.nlp.text_cleaner import remove_html_tags
        result = remove_html_tags("Python &amp; Django &lt;3")
        assert "&amp;" not in result
        assert "&lt;" not in result

    def test_normalize_whitespace(self):
        from app.modules.nlp.text_cleaner import normalize_whitespace
        result = normalize_whitespace("hello    world\n\n\n\nfoo")
        assert "   " not in result
        assert "\n\n\n" not in result

    def test_lowercase_and_strip(self):
        from app.modules.nlp.text_cleaner import lowercase_and_strip
        result = lowercase_and_strip("  Python FASTAPI  ")
        assert result == "python fastapi"

    def test_clean_text_full_pipeline(self):
        from app.modules.nlp.text_cleaner import clean_text
        raw = "<h1>CV</h1><p>Python 3.11 et FastAPI. Docker   et Kubernetes.</p>"
        result = clean_text(raw)
        assert "<" not in result
        assert "  " not in result
        assert "python" in result
        assert "docker" in result

    def test_clean_text_empty_string(self):
        from app.modules.nlp.text_cleaner import clean_text
        assert clean_text("") == ""

    def test_clean_text_only_html(self):
        from app.modules.nlp.text_cleaner import clean_text
        result = clean_text("<div><p><span></span></p></div>")
        assert result.strip() == ""


# ===========================================================================
# Tests unitaires — skill_dictionary.py
# ===========================================================================

class TestSkillDictionary:
    def test_normalize_python_version(self):
        from app.modules.nlp.skill_dictionary import normalize_skill_name
        assert normalize_skill_name("Python 3.11") == "python"
        assert normalize_skill_name("Python 3") == "python"

    def test_normalize_react_alias(self):
        from app.modules.nlp.skill_dictionary import normalize_skill_name
        assert normalize_skill_name("ReactJS") == "react"
        assert normalize_skill_name("React.js") == "react"

    def test_normalize_postgres_alias(self):
        from app.modules.nlp.skill_dictionary import normalize_skill_name
        assert normalize_skill_name("postgres") == "postgresql"

    def test_get_skill_category_known(self):
        from app.modules.nlp.skill_dictionary import get_skill_category
        assert get_skill_category("python") == "languages"
        assert get_skill_category("docker") == "cloud"
        assert get_skill_category("git") == "tools"

    def test_get_skill_category_unknown(self):
        from app.modules.nlp.skill_dictionary import get_skill_category
        assert get_skill_category("cobol_vintage_1960") is None

    def test_load_skill_dictionary_returns_dict(self):
        from app.modules.nlp.skill_dictionary import load_skill_dictionary
        d = load_skill_dictionary()
        assert isinstance(d, dict)
        assert "languages" in d
        assert "frameworks" in d


# ===========================================================================
# Tests unitaires — skill_extractor.py
# ===========================================================================

class TestExtractSkills:
    def _mock_nlp(self, texts=None):
        mock_nlp = MagicMock()
        mock_doc = MagicMock()
        mock_doc.ents = []
        mock_doc.__iter__ = MagicMock(return_value=iter([]))
        mock_nlp.return_value = mock_doc
        return mock_nlp

    def test_extract_python_from_text(self):
        from app.modules.nlp.skill_extractor import extract_skills_from_text
        with patch("app.modules.nlp.skill_extractor._nlp", self._mock_nlp()):
            skills = extract_skills_from_text(
                "experienced python developer with fastapi and postgresql"
            )
        assert "python" in skills
        assert "fastapi" in skills

    def test_extract_deduplicates(self):
        from app.modules.nlp.skill_extractor import extract_skills_from_text
        with patch("app.modules.nlp.skill_extractor._nlp", self._mock_nlp()):
            skills = extract_skills_from_text("python python fastapi fastapi")
        assert len(skills) == len(set(skills))

    def test_extract_empty_text_returns_empty(self):
        from app.modules.nlp.skill_extractor import extract_skills_from_text
        with patch("app.modules.nlp.skill_extractor._nlp", self._mock_nlp()):
            assert extract_skills_from_text("") == []
            assert extract_skills_from_text("   ") == []


# ===========================================================================
# Tests d'intégration — routes NLP
# ===========================================================================

class TestNLPProcessResume:
    async def test_process_resume_success(self, async_client: AsyncClient):
        user = await create_test_user(async_client)
        await create_test_profile(async_client, user["headers"])
        resume = await create_test_resume(async_client, user["headers"])

        # Mock le service NLP complet pour éviter le parsing PDF réel
        with patch("app.modules.nlp.nlp_service.process_resume") as mock_process:
            mock_process.return_value = {
                "skills_extracted": ["python", "fastapi"],
                "user_id": user["id"],
                "resume_id": resume["id"],
                "processing_time_ms": 150,
                "status": "completed"
            }
            resp = await async_client.post(
                f"/api/v1/nlp/process/{resume['id']}",
                headers=user["headers"],
            )
        assert resp.status_code in (200, 201)

    async def test_process_resume_not_found(self, async_client: AsyncClient):
        user = await create_test_user(async_client)
        resp = await async_client.post(
            "/api/v1/nlp/process/99999999",
            headers=user["headers"],
        )
        assert resp.status_code == 404

    async def test_process_resume_other_user_forbidden(self, async_client: AsyncClient):
        user1 = await create_test_user(async_client)
        user2 = await create_test_user(async_client)
        await create_test_profile(async_client, user1["headers"])
        resume = await create_test_resume(async_client, user1["headers"])

        resp = await async_client.post(
            f"/api/v1/nlp/process/{resume['id']}",
            headers=user2["headers"],
        )
        assert resp.status_code == 403

    async def test_process_resume_unauthenticated(self, async_client: AsyncClient):
        resp = await async_client.post("/api/v1/nlp/process/1")
        assert resp.status_code == 401


class TestNLPBulkProcess:
    async def test_bulk_process_profile_success(self, async_client: AsyncClient):
        user = await create_test_user(async_client)
        profile = await create_test_profile(async_client, user["headers"])
        await create_test_resume(async_client, user["headers"])

        resp = await async_client.post(
            f"/api/v1/nlp/process/profile/{profile['id']}",
            headers=user["headers"],
        )
        assert resp.status_code == 200

    async def test_bulk_process_other_profile_forbidden(self, async_client: AsyncClient):
        user1 = await create_test_user(async_client)
        user2 = await create_test_user(async_client)
        profile = await create_test_profile(async_client, user1["headers"])

        resp = await async_client.post(
            f"/api/v1/nlp/process/profile/{profile['id']}",
            headers=user2["headers"],
        )
        assert resp.status_code == 403

    async def test_bulk_process_profile_not_found(self, async_client: AsyncClient):
        user = await create_test_user(async_client)
        resp = await async_client.post(
            "/api/v1/nlp/process/profile/99999999",
            headers=user["headers"],
        )
        assert resp.status_code == 404


class TestNLPStatus:
    async def test_get_nlp_status(self, async_client: AsyncClient):
        user = await create_test_user(async_client)
        await create_test_profile(async_client, user["headers"])
        resume = await create_test_resume(async_client, user["headers"])

        resp = await async_client.get(
            f"/api/v1/nlp/status/{resume['id']}",
            headers=user["headers"],
        )
        assert resp.status_code == 200
        data = resp.json()
        target = data.get("data", data)
        assert any(k in target for k in ("is_parsed", "status", "resume_id"))

    async def test_get_nlp_status_not_found(self, async_client: AsyncClient):
        user = await create_test_user(async_client)
        resp = await async_client.get(
            "/api/v1/nlp/status/99999999",
            headers=user["headers"],
        )
        assert resp.status_code == 404


class TestNLPProfileSkills:
    async def test_get_profile_skills(self, async_client: AsyncClient):
        user = await create_test_user(async_client)
        profile = await create_test_profile(async_client, user["headers"])

        # Mock le service pour retourner un format compatible avec le schéma Pydantic
        with patch("app.modules.nlp.nlp_service.get_profile_skills") as mock_skills:
            mock_skills.return_value = {
                "skills": ["python", "fastapi", "docker"],
                "profile_id": profile["id"],
                "total": 3
            }
            resp = await async_client.get(
                f"/api/v1/nlp/skills/{profile['id']}",
                headers=user["headers"],
            )
        assert resp.status_code in (200, 204)
        if resp.status_code == 200:
            data = resp.json()
            target = data.get("data", data) if isinstance(data, dict) else data
            assert "skills" in target
            assert isinstance(target["skills"], list)

    async def test_get_profile_skills_other_user_forbidden(self, async_client: AsyncClient):
        user1 = await create_test_user(async_client)
        user2 = await create_test_user(async_client)
        profile = await create_test_profile(async_client, user1["headers"])

        resp = await async_client.get(
            f"/api/v1/nlp/skills/{profile['id']}",
            headers=user2["headers"],
        )
        assert resp.status_code == 403


class TestNLPExtractText:
    async def test_extract_text_debug_admin(self, async_client: AsyncClient):
        from app.main import app
        import app.modules.auth.dependencies as auth_deps

        # Crée un user normal et mock les guards pour simuler un admin
        user = await create_test_user(async_client)

        class MockAdmin:
            id = user["id"]
            email = user["email"]
            is_active = True
            is_superuser = True

        async def mock_get_current_user():
            return MockAdmin()

        # Écrase les guards d'authentification
        for attr in dir(auth_deps):
            if any(k in attr for k in ("get_current_", "get_admin_", "get_active_")):
                try:
                    app.dependency_overrides[getattr(auth_deps, attr)] = mock_get_current_user
                except Exception:
                    pass

        try:
            resp = await async_client.post(
                "/api/v1/nlp/extract-text",
                json={"text": "Experienced python developer with docker and kubernetes"},
                headers=user["headers"],
            )
            assert resp.status_code in (200, 201)
        finally:
            app.dependency_overrides.clear()

    async def test_extract_text_non_admin_forbidden(self, async_client: AsyncClient):
        user = await create_test_user(async_client)
        resp = await async_client.post(
            "/api/v1/nlp/extract-text",
            json={"text": "python developer"},
            headers=user["headers"],
        )
        assert resp.status_code == 403

    async def test_extract_text_unauthenticated(self, async_client: AsyncClient):
        resp = await async_client.post(
            "/api/v1/nlp/extract-text",
            json={"text": "python developer"},
        )
        assert resp.status_code == 401


# ===========================================================================
# Pipeline complet
# ===========================================================================

class TestFullNLPPipeline:
    def test_process_resume_full_pipeline_unit(self):
        from app.modules.nlp.text_cleaner import clean_text
        from app.modules.nlp.skill_extractor import extract_skills_from_text

        raw_cv = """
        <h1>John Doe</h1>
        <p>5+ years of experience with Python and FastAPI.</p>
        <p>Experienced in: Docker, Kubernetes, PostgreSQL, Redis.</p>
        <p>Knowledge of AWS and Terraform.</p>
        """
        cleaned = clean_text(raw_cv)

        mock_nlp = MagicMock()
        mock_doc = MagicMock()
        mock_doc.ents = []
        mock_doc.__iter__ = MagicMock(return_value=iter([]))
        mock_nlp.return_value = mock_doc

        with patch("app.modules.nlp.skill_extractor._nlp", mock_nlp):
            skills = extract_skills_from_text(cleaned)

        assert "python" in skills
        assert "fastapi" in skills
        assert "docker" in skills
        assert len(skills) == len(set(skills))

class TestNLPProcessResume:
    @pytest.mark.asyncio
    async def test_process_resume_success(self, async_client: AsyncClient):
        ...        