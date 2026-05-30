# test_auth_route.py
from app.main import app

print("=== Routes avec 'auth' ===")
for route in app.routes:
    if 'auth' in str(route.path):
        print(f"  {route.path}")

print("\n=== Toutes les routes API ===")
for route in app.routes:
    if '/api/v1' in str(route.path):
        print(f"  {route.path}")