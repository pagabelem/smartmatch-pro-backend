"""
Tests for users module.
"""

import pytest
from fastapi.testclient import TestClient


class TestUsers:
    """Test suite for users endpoints."""

    def test_get_current_user_info(self, client: TestClient, auth_headers):
        """Test GET /api/v1/users/me."""
        response = client.get("/api/v1/users/me", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        # La réponse est directement l'utilisateur, pas encapsulée dans {"data": ...}
        assert data["id"] is not None
        assert "email" in data

    def test_get_user_by_id_own(self, client: TestClient, auth_headers):
        """Test user can get their own information."""
        # D'abord obtenir l'ID via /me
        me_response = client.get("/api/v1/users/me", headers=auth_headers)
        user_id = me_response.json()["id"]
        
        response = client.get(f"/api/v1/users/{user_id}", headers=auth_headers)
        assert response.status_code == 200

    def test_list_users_admin_only(self, client: TestClient, admin_auth_headers, user_token):
        """Test only admin can list all users."""
        # Regular user gets 403
        user_headers = {"Authorization": f"Bearer {user_token}"}
        response = client.get("/api/v1/users/", headers=user_headers)
        assert response.status_code == 403

        # Admin gets 200
        response = client.get("/api/v1/users/", headers=admin_auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert "items" in data
        assert "total" in data