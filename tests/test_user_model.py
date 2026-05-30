def test_user_model_structure(client, setup_database, mock_db_check):
    """Affiche la structure du modèle User"""
    register_data = {
        "email": "model_test@example.com",
        "password": "Test123!@#",
        "full_name": "Model Test"
    }
    
    response = client.post("/api/v1/auth/register", json=register_data)
    assert response.status_code == 201
    
    user_data = response.json()["data"]["user"]
    print("\n=== Structure du modèle User ===")
    for key, value in user_data.items():
        print(f"  {key}: {value} ({type(value).__name__})")