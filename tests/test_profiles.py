"""
Tests for profiles module.
"""

import pytest
from fastapi.testclient import TestClient


class TestProfiles:
    """Test suite for profiles endpoints."""

    def test_get_my_profile(self, client: TestClient, auth_headers):
        """Test getting own profile."""
        response = client.get("/api/v1/profiles/me", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["id"] is not None

    def test_update_profile(self, client: TestClient, auth_headers):
        """Test updating profile."""
        # Get existing profile
        get_resp = client.get("/api/v1/profiles/me", headers=auth_headers)
        profile_id = get_resp.json()["id"]
        
        response = client.put(
            f"/api/v1/profiles/{profile_id}",
            headers=auth_headers,
            json={"title": "Senior Engineer", "experience_years": 5},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["title"] == "Senior Engineer"
        assert data["experience_years"] == 5

    def test_get_profile_by_id(self, client: TestClient, auth_headers):
        """Test getting profile by ID."""
        get_resp = client.get("/api/v1/profiles/me", headers=auth_headers)
        profile_id = get_resp.json()["id"]
        
        response = client.get(f"/api/v1/profiles/{profile_id}", headers=auth_headers)
        assert response.status_code == 200

    def test_list_profiles_admin_only(self, client: TestClient, admin_auth_headers, user_token):
        """Test only admin can list all profiles."""
        # Regular user = 403
        resp = client.get("/api/v1/profiles/", headers={"Authorization": f"Bearer {user_token}"})
        assert resp.status_code == 403

        # Admin = 200
        resp = client.get("/api/v1/profiles/", headers=admin_auth_headers)
        assert resp.status_code == 200
        assert "items" in resp.json()

    def test_search_profiles_by_skill(self, client: TestClient, auth_headers):
        """Test searching profiles by skill."""
        # Get existing profile
        get_resp = client.get("/api/v1/profiles/me", headers=auth_headers)
        profile_id = get_resp.json()["id"]
        
        # Update with skills
        client.put(
            f"/api/v1/profiles/{profile_id}",
            headers=auth_headers,
            json={"skills_raw": ["python", "fastapi"]},
        )
        
        response = client.get(
            "/api/v1/profiles/search/by-skill?skill=python",
            headers=auth_headers,
        )
        assert response.status_code == 200

    def test_delete_profile(self, client: TestClient, admin_auth_headers):
        """Test delete profile (admin only)."""
        # Get admin profile
        get_resp = client.get("/api/v1/profiles/me", headers=admin_auth_headers)
        profile_id = get_resp.json()["id"]
        
        response = client.delete(f"/api/v1/profiles/{profile_id}", headers=admin_auth_headers)
        assert response.status_code == 204

    def test_update_skills_extracted(self, client: TestClient, admin_auth_headers):
        """Test updating extracted skills."""
        # Get admin profile
        get_resp = client.get("/api/v1/profiles/me", headers=admin_auth_headers)
        profile_id = get_resp.json()["id"]
        
        response = client.put(
            f"/api/v1/profiles/{profile_id}",
            headers=admin_auth_headers,
            json={"skills_raw": ["Python", "FastAPI"]},
        )
        assert response.status_code == 200