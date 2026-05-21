"""
Test simple pour vérifier les routes users
"""
from starlette.testclient import TestClient


def test_users_routes_exist(client: TestClient):
    """
    Vérifie que les routes users sont accessibles
    """
    # Créer un utilisateur
    register_data = {
        "email": "test_routes@example.com",
        "password": "Test123!@#",
        "full_name": "Test Routes"
    }
    
    register_response = client.post("/api/v1/auth/register", json=register_data)
    assert register_response.status_code == 201
    token = register_response.json()["data"]["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    
    # Tester GET /api/v1/users/me
    response = client.get("/api/v1/users/me", headers=headers)
    print(f"GET /api/v1/users/me: {response.status_code}")
    if response.status_code == 200:
        print("✅ Route /me fonctionne!")
        print(f"Response: {response.json()}")
    
    # Tester GET /api/v1/users/
    response = client.get("/api/v1/users/", headers=headers)
    print(f"GET /api/v1/users/: {response.status_code}")
    
    # Tester GET /api/v1/users (sans slash)
    response = client.get("/api/v1/users", headers=headers)
    print(f"GET /api/v1/users: {response.status_code}")
    
    # Tester GET avec un ID
    user_id = register_response.json()["data"]["user"]["id"]
    response = client.get(f"/api/v1/users/{user_id}", headers=headers)
    print(f"GET /api/v1/users/{user_id}: {response.status_code}")
    
    response = client.get(f"/api/v1/users/{user_id}/", headers=headers)
    print(f"GET /api/v1/users/{user_id}/: {response.status_code}")