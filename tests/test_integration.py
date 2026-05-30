"""
Integration tests for complete user flows.
"""

import pytest
from fastapi.testclient import TestClient


class TestIntegration:
    """Integration test suite for end-to-end flows."""

    def test_complete_user_flow(self, client: TestClient):
        """Test complete user journey: register → login → profile → update."""
        # 1. Register
        register_response = client.post(
            "/api/v1/auth/register",
            json={
                "email": "flowuser@example.com",
                "password": "FlowPass123!",
            },
        )
        assert register_response.status_code == 201
        token = register_response.json()["data"]["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        # 2. Get current user
        me_response = client.get("/api/v1/auth/me", headers=headers)
        assert me_response.status_code == 200
        user_id = me_response.json()["data"]["id"]

        # 3. Create profile
        profile_response = client.post(
            "/api/v1/profiles/",
            headers=headers,
            json={
                "full_name": "Flow User",
                "title": "Software Engineer",
                "location": "Casablanca",
                "experience_years": 3,
            },
        )
        assert profile_response.status_code == 201
        profile_id = profile_response.json()["id"]

        # 4. Get profile
        get_profile = client.get(f"/api/v1/profiles/{profile_id}", headers=headers)
        assert get_profile.status_code == 200
        assert get_profile.json()["full_name"] == "Flow User"

        # 5. Update profile
        update_response = client.put(
            f"/api/v1/profiles/{profile_id}",
            headers=headers,
            json={"title": "Senior Software Engineer"},
        )
        assert update_response.status_code == 200
        assert update_response.json()["title"] == "Senior Software Engineer"

        # 6. Get user info
        user_response = client.get(f"/api/v1/users/{user_id}", headers=headers)
        assert user_response.status_code == 200

    def test_admin_flow(self, client: TestClient, test_admin):
        """Test admin flow: login → list users → list profiles."""
        # Login as admin
        login_response = client.post(
            "/api/v1/auth/login",
            data={
                "username": "admin@example.com",
                "password": "Admin123!@#",
            },
        )
        assert login_response.status_code == 200
        token = login_response.json()["data"]["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        # List all users
        users_response = client.get("/api/v1/users/", headers=headers)
        assert users_response.status_code == 200
        assert users_response.json()["total"] >= 1

        # List all profiles
        profiles_response = client.get("/api/v1/profiles/", headers=headers)
        assert profiles_response.status_code == 200

    def test_profile_skill_extraction_flow(self, client: TestClient, auth_headers, test_profile):
        """Test skill extraction and search flow."""
        # Update profile with skills
        client.put(
            f"/api/v1/profiles/{test_profile.id}",
            headers=auth_headers,
            json={"skills_raw": "I have experience with Python, FastAPI, and PostgreSQL"},
        )

        # Search by skill
        search_response = client.get(
            "/api/v1/profiles/search/by-skill?skill=python",
            headers=auth_headers,
        )
        assert search_response.status_code == 200