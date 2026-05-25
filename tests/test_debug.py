# tests/test_debug.py
import pytest
from fastapi.testclient import TestClient


def test_auth_headers_work(auth_headers, client, test_user):
    """Test that auth_headers contains a valid token."""
    print(f"\nHeaders: {auth_headers}")
    
    # Test the token with /auth/me
    response = client.get("/api/v1/auth/me", headers=auth_headers)
    print(f"GET /auth/me status: {response.status_code}")
    if response.status_code == 200:
        print(f"User: {response.json()['data']['email']}")
    
    assert response.status_code == 200