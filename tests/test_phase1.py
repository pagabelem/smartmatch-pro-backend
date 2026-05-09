"""
tests/test_phase1.py — Tests Phase 1 : Auth JWT + Module Skills.

Fixtures db, client, reset_tables viennent de conftest.py — rien à redéfinir ici.

Coverage
--------
  TestAuthRegister     POST /api/v1/auth/register
  TestAuthLogin        POST /api/v1/auth/login
  TestAuthRefresh      POST /api/v1/auth/refresh
  TestAuthLogout       POST /api/v1/auth/logout  +  /logout-all
  TestAuthMe           GET  /api/v1/auth/me
  TestSkillsCreate     POST /api/v1/skills/
  TestSkillsRead       GET  /api/v1/skills/  +  /{id}
  TestSkillsUpdate     PUT  /api/v1/skills/{id}
  TestSkillsDelete     DELETE /api/v1/skills/{id}
  TestSkillsPagination pagination + search + filtre skill_type
  TestSkillService     tests unitaires service (sans HTTP)

Run :
    python -m pytest tests/test_phase1.py -v
"""

import pytest


# ── Helpers ───────────────────────────────────────────────────────────────────
VALID_USER  = {"email": "alice@example.com", "password": "Secure1!"}
VALID_USER2 = {"email": "bob@example.com",   "password": "Another1!"}


def register(client, user=None):
    """Inscrit un utilisateur et retourne le dict data (tokens + user)."""
    user = user or VALID_USER
    r = client.post("/api/v1/auth/register", json=user)
    assert r.status_code == 201, r.text
    return r.json()["data"]


def headers(token_data: dict) -> dict:
    return {"Authorization": f"Bearer {token_data['access_token']}"}


def create_skill(client, h, name="python", display_name="Python"):
    return client.post(
        "/api/v1/skills/",
        json={"name": name, "display_name": display_name},
        headers=h,
    )


# ══════════════════════════════════════════════════════════════════════════════
# AUTH — REGISTER
# ══════════════════════════════════════════════════════════════════════════════
class TestAuthRegister:

    def test_register_success(self, client):
        r = client.post("/api/v1/auth/register", json=VALID_USER)
        assert r.status_code == 201
        data = r.json()["data"]
        assert "access_token"  in data
        assert "refresh_token" in data
        assert data["token_type"] == "Bearer"
        assert data["user"]["email"] == VALID_USER["email"]

    def test_register_creates_profile(self, client, db):
        client.post("/api/v1/auth/register", json={
            **VALID_USER, "first_name": "Alice", "last_name": "Martin"
        })
        from app.modules.users.user_model import Profile, User
        user = db.query(User).filter(User.email == VALID_USER["email"]).first()
        assert user is not None
        assert user.profile is not None
        assert user.profile.first_name == "Alice"
        assert user.profile.last_name  == "Martin"

    def test_register_duplicate_email(self, client):
        client.post("/api/v1/auth/register", json=VALID_USER)
        r = client.post("/api/v1/auth/register", json=VALID_USER)
        assert r.status_code == 409
        assert r.json()["error"]["code"] == "EMAIL_ALREADY_EXISTS"

    def test_register_weak_password(self, client):
        r = client.post("/api/v1/auth/register", json={
            "email": "x@example.com", "password": "weak"
        })
        assert r.status_code == 422

    def test_register_no_uppercase(self, client):
        r = client.post("/api/v1/auth/register", json={
            "email": "x@example.com", "password": "alllower1"
        })
        assert r.status_code == 422

    def test_register_no_digit(self, client):
        r = client.post("/api/v1/auth/register", json={
            "email": "x@example.com", "password": "NoDigitHere"
        })
        assert r.status_code == 422

    def test_register_invalid_email(self, client):
        r = client.post("/api/v1/auth/register", json={
            "email": "not-an-email", "password": "Secure1!"
        })
        assert r.status_code == 422

    def test_register_stores_hashed_password(self, client, db):
        client.post("/api/v1/auth/register", json=VALID_USER)
        from app.modules.users.user_model import User
        user = db.query(User).first()
        assert user.hashed_password != VALID_USER["password"]
        assert len(user.hashed_password) > 20

    def test_register_email_case_insensitive(self, client):
        """Alice@Example.COM et alice@example.com = même compte."""
        client.post("/api/v1/auth/register", json={
            "email": "Alice@Example.COM", "password": "Secure1!"
        })
        r = client.post("/api/v1/auth/register", json={
            "email": "alice@example.com", "password": "Secure1!"
        })
        assert r.status_code == 409


# ══════════════════════════════════════════════════════════════════════════════
# AUTH — LOGIN
# ══════════════════════════════════════════════════════════════════════════════
class TestAuthLogin:

    def test_login_success(self, client):
        register(client)
        r = client.post("/api/v1/auth/login", json=VALID_USER)
        assert r.status_code == 200
        data = r.json()["data"]
        assert "access_token"  in data
        assert "refresh_token" in data

    def test_login_wrong_password(self, client):
        register(client)
        r = client.post("/api/v1/auth/login", json={
            "email": VALID_USER["email"], "password": "WrongPass1"
        })
        assert r.status_code == 401
        assert r.json()["error"]["code"] == "INVALID_CREDENTIALS"

    def test_login_wrong_email(self, client):
        """Même code d'erreur pour email inconnu — anti-énumération."""
        r = client.post("/api/v1/auth/login", json={
            "email": "nobody@example.com", "password": "Secure1!"
        })
        assert r.status_code == 401
        assert r.json()["error"]["code"] == "INVALID_CREDENTIALS"

    def test_login_updates_last_login_at(self, client, db):
        register(client)
        client.post("/api/v1/auth/login", json=VALID_USER)
        from app.modules.users.user_model import User
        user = db.query(User).first()
        assert user.last_login_at is not None

    def test_login_inactive_account(self, client, db):
        register(client)
        from app.modules.users.user_model import User
        user = db.query(User).first()
        user.is_active = False
        db.commit()
        r = client.post("/api/v1/auth/login", json=VALID_USER)
        assert r.status_code == 401


# ══════════════════════════════════════════════════════════════════════════════
# AUTH — REFRESH
# ══════════════════════════════════════════════════════════════════════════════
class TestAuthRefresh:

    def test_refresh_returns_new_tokens(self, client):
        tokens = register(client)
        r = client.post("/api/v1/auth/refresh",
                        json={"refresh_token": tokens["refresh_token"]})
        assert r.status_code == 200
        new = r.json()["data"]
        assert "access_token" in new
        # Le nouveau access token doit être différent de l'ancien
        assert new["access_token"] != tokens["access_token"]

    def test_refresh_token_rotation(self, client):
        """Chaque refresh produit un nouveau refresh_token."""
        tokens = register(client)
        r = client.post("/api/v1/auth/refresh",
                        json={"refresh_token": tokens["refresh_token"]})
        new = r.json()["data"]
        assert new["refresh_token"] != tokens["refresh_token"]

    def test_refresh_old_token_revoked(self, client):
        """Réutiliser l'ancien token après rotation doit échouer."""
        tokens = register(client)
        # Premier refresh — OK
        client.post("/api/v1/auth/refresh",
                    json={"refresh_token": tokens["refresh_token"]})
        # Deuxième usage du MÊME ancien token — doit échouer
        r = client.post("/api/v1/auth/refresh",
                        json={"refresh_token": tokens["refresh_token"]})
        assert r.status_code == 401

    def test_refresh_invalid_token(self, client):
        r = client.post("/api/v1/auth/refresh",
                        json={"refresh_token": "not.a.valid.token"})
        assert r.status_code == 401


# ══════════════════════════════════════════════════════════════════════════════
# AUTH — LOGOUT
# ══════════════════════════════════════════════════════════════════════════════
class TestAuthLogout:

    def test_logout_revokes_refresh_token(self, client):
        tokens = register(client)
        r = client.post("/api/v1/auth/logout",
                        json={"refresh_token": tokens["refresh_token"]})
        assert r.status_code == 200
        # Le token révoqué ne peut plus servir à se rafraîchir
        r2 = client.post("/api/v1/auth/refresh",
                         json={"refresh_token": tokens["refresh_token"]})
        assert r2.status_code == 401

    def test_logout_all_revokes_all_sessions(self, client):
        tokens1 = register(client)
        # Deuxième login = deuxième refresh token
        tokens2 = client.post("/api/v1/auth/login",
                              json=VALID_USER).json()["data"]

        r = client.post("/api/v1/auth/logout-all",
                        headers=headers(tokens1))
        assert r.status_code == 200

        # Les deux tokens doivent être invalidés
        r1 = client.post("/api/v1/auth/refresh",
                         json={"refresh_token": tokens1["refresh_token"]})
        r2 = client.post("/api/v1/auth/refresh",
                         json={"refresh_token": tokens2["refresh_token"]})
        assert r1.status_code == 401
        assert r2.status_code == 401


# ══════════════════════════════════════════════════════════════════════════════
# AUTH — ME
# ══════════════════════════════════════════════════════════════════════════════
class TestAuthMe:

    def test_me_returns_current_user(self, client):
        tokens = register(client)
        r = client.get("/api/v1/auth/me", headers=headers(tokens))
        assert r.status_code == 200
        data = r.json()["data"]
        assert data["email"] == VALID_USER["email"]

    def test_me_requires_auth(self, client):
        r = client.get("/api/v1/auth/me")
        assert r.status_code == 401

    def test_me_invalid_token(self, client):
        r = client.get("/api/v1/auth/me",
                       headers={"Authorization": "Bearer fake.token"})
        assert r.status_code == 401


# ══════════════════════════════════════════════════════════════════════════════
# SKILLS — CREATE
# ══════════════════════════════════════════════════════════════════════════════
class TestSkillsCreate:

    def test_create_skill_success(self, client):
        tokens = register(client)
        r = create_skill(client, headers(tokens))
        assert r.status_code == 201
        data = r.json()["data"]
        assert data["name"]         == "python"
        assert data["display_name"] == "Python"
        assert data["skill_type"]   == "hard"
        assert "id" in data

    def test_create_normalises_name_to_lowercase(self, client):
        tokens = register(client)
        r = client.post("/api/v1/skills/",
                        json={"name": "  ReactJS  "},
                        headers=headers(tokens))
        assert r.status_code == 201
        assert r.json()["data"]["name"] == "reactjs"

    def test_create_duplicate_returns_409(self, client):
        tokens = register(client)
        h = headers(tokens)
        create_skill(client, h)
        r = create_skill(client, h)
        assert r.status_code == 409

    def test_create_with_category(self, client):
        tokens = register(client)
        r = client.post("/api/v1/skills/",
                        json={"name": "pytorch", "category": "ai_ml"},
                        headers=headers(tokens))
        assert r.status_code == 201
        assert r.json()["data"]["category"] == "ai_ml"

    def test_create_soft_skill(self, client):
        tokens = register(client)
        r = client.post("/api/v1/skills/",
                        json={"name": "communication", "skill_type": "soft"},
                        headers=headers(tokens))
        assert r.status_code == 201
        assert r.json()["data"]["skill_type"] == "soft"

    def test_create_name_too_short_returns_422(self, client):
        tokens = register(client)
        r = client.post("/api/v1/skills/",
                        json={"name": "x"},
                        headers=headers(tokens))
        assert r.status_code == 422

    def test_create_requires_auth(self, client):
        r = create_skill(client, {})
        assert r.status_code == 401


# ══════════════════════════════════════════════════════════════════════════════
# SKILLS — READ
# ══════════════════════════════════════════════════════════════════════════════
class TestSkillsRead:

    def test_get_by_id(self, client):
        tokens = register(client)
        h = headers(tokens)
        skill_id = create_skill(client, h).json()["data"]["id"]
        r = client.get(f"/api/v1/skills/{skill_id}", headers=h)
        assert r.status_code == 200
        assert r.json()["data"]["name"] == "python"

    def test_get_not_found_returns_404(self, client):
        tokens = register(client)
        r = client.get("/api/v1/skills/9999", headers=headers(tokens))
        assert r.status_code == 404
        assert r.json()["error"]["code"] == "NOT_FOUND"

    def test_list_empty(self, client):
        tokens = register(client)
        r = client.get("/api/v1/skills/", headers=headers(tokens))
        assert r.status_code == 200
        assert r.json()["data"]["total"] == 0
        assert r.json()["data"]["items"] == []

    def test_list_returns_all_skills(self, client):
        tokens = register(client)
        h = headers(tokens)
        create_skill(client, h, "python",     "Python")
        create_skill(client, h, "sql",        "SQL")
        create_skill(client, h, "tensorflow", "TensorFlow")
        r = client.get("/api/v1/skills/", headers=h)
        assert r.json()["data"]["total"] == 3

    def test_list_alphabetical_by_default(self, client):
        tokens = register(client)
        h = headers(tokens)
        create_skill(client, h, "tensorflow", "TensorFlow")
        create_skill(client, h, "python",     "Python")
        create_skill(client, h, "java",       "Java")
        r = client.get("/api/v1/skills/?sort=name", headers=h)
        names = [s["name"] for s in r.json()["data"]["items"]]
        assert names == sorted(names)

    def test_list_requires_auth(self, client):
        r = client.get("/api/v1/skills/")
        assert r.status_code == 401


# ══════════════════════════════════════════════════════════════════════════════
# SKILLS — SEARCH & PAGINATION
# ══════════════════════════════════════════════════════════════════════════════
class TestSkillsPagination:

    def _seed(self, client, h, n=15):
        for i in range(n):
            create_skill(client, h, f"skill{i:02d}", f"Skill{i:02d}")

    def test_search_filters_by_name(self, client):
        tokens = register(client)
        h = headers(tokens)
        create_skill(client, h, "python",     "Python")
        create_skill(client, h, "pytorch",    "PyTorch")
        create_skill(client, h, "javascript", "JavaScript")
        r = client.get("/api/v1/skills/?search=py", headers=h)
        data = r.json()["data"]
        assert data["total"] == 2
        names = {s["name"] for s in data["items"]}
        assert "python"  in names
        assert "pytorch" in names

    def test_filter_by_skill_type(self, client):
        tokens = register(client)
        h = headers(tokens)
        client.post("/api/v1/skills/",
                    json={"name": "python",        "skill_type": "hard"}, headers=h)
        client.post("/api/v1/skills/",
                    json={"name": "communication", "skill_type": "soft"}, headers=h)
        r = client.get("/api/v1/skills/?skill_type=soft", headers=h)
        data = r.json()["data"]
        assert data["total"] == 1
        assert data["items"][0]["name"] == "communication"

    def test_pagination_first_page(self, client):
        tokens = register(client)
        h = headers(tokens)
        self._seed(client, h, 15)
        r = client.get("/api/v1/skills/?page=1&page_size=5", headers=h)
        data = r.json()["data"]
        assert len(data["items"]) == 5
        assert data["total"]      == 15
        assert data["pages"]      == 3
        assert data["has_next"]   is True
        assert data["has_prev"]   is False

    def test_pagination_last_page(self, client):
        tokens = register(client)
        h = headers(tokens)
        self._seed(client, h, 13)
        r = client.get("/api/v1/skills/?page=3&page_size=5", headers=h)
        data = r.json()["data"]
        assert len(data["items"]) == 3
        assert data["has_next"]   is False
        assert data["has_prev"]   is True


# ══════════════════════════════════════════════════════════════════════════════
# SKILLS — UPDATE
# ══════════════════════════════════════════════════════════════════════════════
class TestSkillsUpdate:

    def test_update_display_name(self, client):
        tokens = register(client)
        h = headers(tokens)
        skill_id = create_skill(client, h).json()["data"]["id"]
        r = client.put(f"/api/v1/skills/{skill_id}",
                       json={"display_name": "Python 3.12"}, headers=h)
        assert r.status_code == 200
        assert r.json()["data"]["display_name"] == "Python 3.12"

    def test_update_category(self, client):
        tokens = register(client)
        h = headers(tokens)
        skill_id = create_skill(client, h).json()["data"]["id"]
        r = client.put(f"/api/v1/skills/{skill_id}",
                       json={"category": "programming"}, headers=h)
        assert r.status_code == 200
        assert r.json()["data"]["category"] == "programming"

    def test_update_name_conflict_returns_409(self, client):
        tokens = register(client)
        h = headers(tokens)
        s1_id = create_skill(client, h, "python", "Python").json()["data"]["id"]
        create_skill(client, h, "java", "Java")
        r = client.put(f"/api/v1/skills/{s1_id}",
                       json={"name": "java"}, headers=h)
        assert r.status_code == 409

    def test_update_nonexistent_returns_404(self, client):
        tokens = register(client)
        r = client.put("/api/v1/skills/9999",
                       json={"display_name": "X"},
                       headers=headers(tokens))
        assert r.status_code == 404


# ══════════════════════════════════════════════════════════════════════════════
# SKILLS — DELETE
# ══════════════════════════════════════════════════════════════════════════════
class TestSkillsDelete:

    def test_delete_skill(self, client):
        tokens = register(client)
        h = headers(tokens)
        skill_id = create_skill(client, h).json()["data"]["id"]
        r = client.delete(f"/api/v1/skills/{skill_id}", headers=h)
        assert r.status_code == 204
        # Confirmation : plus accessible
        r2 = client.get(f"/api/v1/skills/{skill_id}", headers=h)
        assert r2.status_code == 404

    def test_delete_nonexistent_returns_404(self, client):
        tokens = register(client)
        r = client.delete("/api/v1/skills/9999", headers=headers(tokens))
        assert r.status_code == 404

    def test_delete_requires_auth(self, client):
        tokens = register(client)
        h = headers(tokens)
        skill_id = create_skill(client, h).json()["data"]["id"]
        r = client.delete(f"/api/v1/skills/{skill_id}")
        assert r.status_code == 401


# ══════════════════════════════════════════════════════════════════════════════
# SKILL SERVICE — Tests unitaires (sans HTTP)
# ══════════════════════════════════════════════════════════════════════════════
class TestSkillService:

    def test_bulk_upsert_creates_new_skills(self, db):
        from app.modules.skills.skill_service import bulk_upsert
        skills = bulk_upsert(db, ["Python", "SQL", "TensorFlow"])
        assert len(skills) == 3
        assert {s.name for s in skills} == {"python", "sql", "tensorflow"}

    def test_bulk_upsert_is_idempotent(self, db):
        from app.modules.skills.skill_model import Skill
        from app.modules.skills.skill_service import bulk_upsert
        bulk_upsert(db, ["Python", "SQL"])
        bulk_upsert(db, ["Python", "Java"])  # Python existe déjà
        assert db.query(Skill).count() == 3  # python, sql, java

    def test_bulk_upsert_skips_empty_strings(self, db):
        from app.modules.skills.skill_service import bulk_upsert
        skills = bulk_upsert(db, ["", "   ", "python"])
        assert len(skills) == 1

    def test_get_skill_by_name(self, db):
        from app.modules.skills.skill_service import bulk_upsert, get_skill_by_name
        bulk_upsert(db, ["Python"])
        assert get_skill_by_name(db, "python")       is not None
        assert get_skill_by_name(db, "PYTHON")       is not None
        assert get_skill_by_name(db, "  Python  ")   is not None
        assert get_skill_by_name(db, "nonexistent")  is None