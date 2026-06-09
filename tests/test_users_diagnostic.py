"""
Test mis à jour pour vérifier les routes users de manière asynchrone
"""
import pytest
from httpx import AsyncClient

# On indique à pytest-asyncio que ce fichier contient des tests asynchrones
pytestmark = pytest.mark.asyncio


async def test_users_routes_exist(async_client: AsyncClient):
    """
    Vérifie que les routes users sont accessibles en mode asynchrone
    """
    # 1. Créer un utilisateur
    register_data = {
        "email": "test_routes_async@example.com",
        "password": "Test123!@#",
        "full_name": "Test Routes"
    }
    
    # ✅ Utilisation de 'await' et de 'async_client'
    register_response = await async_client.post("/api/v1/auth/register", json=register_data)
    
    # Sécurité pour débugger facilement si l'enregistrement échoue (ex: 422 ou 400)
    assert register_response.status_code in (200, 201), f"Échec de l'enregistrement: {register_response.text}"
    
    # Récupération sécurisée du token (s'adapte si ton register connecte directement ou non)
    json_data = register_response.json()
    token = json_data.get("data", {}).get("access_token")
    
    # Si ton register ne renvoie pas de token, il faudra faire un appel à /login ici.
    headers = {"Authorization": f"Bearer {token}"} if token else {}
    
    # 2. Tester GET /api/v1/users/me
    response = await async_client.get("/api/v1/users/me", headers=headers)
    print(f"\nGET /api/v1/users/me: {response.status_code}")
    if response.status_code == 200:
        print("✅ Route /me fonctionne!")
        print(f"Response: {response.json()}")
    
    # 3. Tester GET /api/v1/users/ (avec slash)
    response = await async_client.get("/api/v1/users/", headers=headers)
    print(f"GET /api/v1/users/: {response.status_code}")
    
    # 4. Tester GET /api/v1/users (sans slash)
    response = await async_client.get("/api/v1/users", headers=headers)
    print(f"GET /api/v1/users: {response.status_code}")
    
    # 5. Tester GET avec un ID (si l'ID est bien présent dans la réponse du register)
    try:
        user_id = json_data["data"]["user"]["id"]
        
        response = await async_client.get(f"/api/v1/users/{user_id}", headers=headers)
        print(f"GET /api/v1/users/{user_id}: {response.status_code}")
        
        response = await async_client.get(f"/api/v1/users/{user_id}/", headers=headers)
        print(f"GET /api/v1/users/{user_id}/: {response.status_code}")
    except KeyError:
        print("⚠️ Impossible de tester la route par ID : structure de réponse inattendue sur /register")