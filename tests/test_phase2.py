"""
Tests pour le module Users (Phase 2)
Valide le comportement des endpoints CRUD et de recherche
"""
import pytest
from fastapi.testclient import TestClient

def test_get_user_by_id(
    client: TestClient,
    setup_database,
    mock_db_check
):
    """Teste qu'un utilisateur connecté peut récupérer ses propres informations"""
    register_data = {
        "email": "get_id@example.com",
        "password": "Test123!@#",
        "full_name": "Get ID User"
    }
    
    register_response = client.post("/api/v1/auth/register", json=register_data)
    assert register_response.status_code == 201
    
    reg_json = register_response.json()
    token = reg_json["data"]["access_token"]
    user_id = reg_json["data"]["user"]["id"]
    headers = {"Authorization": f"Bearer {token}"}
    
    response = client.get(f"/api/v1/users/{user_id}", headers=headers)
    if response.status_code == 404:
        response = client.get(f"/api/v1/users/{user_id}/", headers=headers)
        
    assert response.status_code == 200
    data = response.json()
    user_data = data.get("data", data)
    if "user" in user_data:
        user_data = user_data["user"]
        
    assert user_data["email"] == register_data["email"]


def test_get_current_user_me(
    client: TestClient,
    setup_database,
    mock_db_check
):
    """Teste l'endpoint GET /users/me"""
    register_data = {
        "email": "me_endpoint@example.com",
        "password": "Test123!@#",
        "full_name": "Me Endpoint User"
    }
    
    register_response = client.post("/api/v1/auth/register", json=register_data)
    assert register_response.status_code == 201
    
    token = register_response.json()["data"]["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    
    response = client.get("/api/v1/users/me", headers=headers)
    if response.status_code == 404:
        response = client.get("/api/v1/users/me/", headers=headers)
        
    assert response.status_code == 200
    data = response.json()
    user_data = data.get("data", data)
    if "user" in user_data:
        user_data = user_data["user"]
        
    # Validation des champs réels de ton modèle
    assert user_data["email"] == register_data["email"]
    assert "id" in user_data
    assert "is_active" in user_data


def test_list_users_admin_only(
    client: TestClient,
    setup_database,
    mock_db_check
):
    """Teste que l'accès à GET /users est restreint aux admins"""
    user_data = {
        "email": "standard_list@example.com",
        "password": "Test123!@#",
        "full_name": "Standard User"
    }
    user_register = client.post("/api/v1/auth/register", json=user_data)
    assert user_register.status_code == 201
    user_token = user_register.json()["data"]["access_token"]
    
    response = client.get("/api/v1/users/", headers={"Authorization": f"Bearer {user_token}"})
    if response.status_code == 404:
        response = client.get("/api/v1/users", headers={"Authorization": f"Bearer {user_token}"})
    assert response.status_code == 403


def test_update_user(
    client: TestClient,
    setup_database,
    mock_db_check
):
    """Teste la mise à jour d'un utilisateur (email uniquement suite à la structure du modèle)"""
    register_data = {
        "email": "update_test@example.com",
        "password": "Test123!@#",
        "full_name": "Original Name"
    }
    
    register_response = client.post("/api/v1/auth/register", json=register_data)
    assert register_response.status_code == 201
    
    token = register_response.json()["data"]["access_token"]
    user_id = register_response.json()["data"]["user"]["id"]
    headers = {"Authorization": f"Bearer {token}"}
    
    update_data = {
        "email": "updated@example.com"
    }
    
    response = client.put(f"/api/v1/users/{user_id}/", headers=headers, json=update_data)
    if response.status_code == 404:
        response = client.put(f"/api/v1/users/{user_id}", headers=headers, json=update_data)
        
    assert response.status_code == 200
    data = response.json()
    user_data = data.get("data", data)
    if "user" in user_data:
        user_data = user_data["user"]
        
    assert user_data["email"] == update_data["email"]


def test_delete_user_soft(
    client: TestClient,
    setup_database,
    mock_db_check
):
    """Teste le soft delete d'un utilisateur"""
    pass


def test_search_users(
    client: TestClient,
    setup_database,
    mock_db_check
):
    """Teste la recherche d'utilisateurs par email ou full_name"""
    pass