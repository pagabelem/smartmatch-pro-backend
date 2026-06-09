"""
SmartMatch Pro — Création Admin (Async) — Version universelle
============================================================

Cette version importe l'application complète (comme uvicorn le fait)
pour résoudre automatiquement toutes les dépendances SQLAlchemy.

Usage :
    python create_admin.py
"""

import asyncio
import sys
from pathlib import Path

# Ajouter le dossier parent au path
sys.path.insert(0, str(Path(__file__).parent))

# ============================================================
# SOLUTION : Importer l'application complète (comme main.py)
# Cela charge TOUS les modèles et résout les dépendances
# ============================================================

print("🔧 Chargement de l'application...")

# Import minimal qui charge tous les modèles via l'app
from app.main import app  # noqa: F401
from app.database import AsyncSessionLocal
from app.core.security import hash_password
from sqlalchemy import select

# Maintenant les modèles sont tous chargés
from app.modules.auth.auth_model import User


async def create_admin():
    """Créer un utilisateur admin dans la base de données (async)."""

    print("🔧 Création d'un utilisateur admin...")
    print("-" * 50)

    async with AsyncSessionLocal() as session:
        # Vérifier si l'admin existe déjà
        result = await session.execute(
            select(User).where(User.email == "admin@smartmatch.pro")
        )
        existing = result.scalar_one_or_none()

        if existing:
            print(f"ℹ️  Admin déjà existant — ID: {existing.id}")
            print(f"   Email: admin@smartmatch.pro")
            print(f"   is_superuser: {existing.is_superuser}")

            # S'assurer qu'il est bien admin
            if not existing.is_superuser:
                existing.is_superuser = True
                await session.commit()
                print("✅ is_superuser mis à jour: True")
            else:
                print("✅ Déjà admin, aucune modification nécessaire")

            return existing

        # Créer le nouvel admin
        admin = User(
            email="admin@smartmatch.pro",
            hashed_password=hash_password("Admin123!@#"),
            is_active=True,
            is_superuser=True,
        )

        session.add(admin)
        await session.commit()
        await session.refresh(admin)

        print(f"✅ Admin créé avec succès !")
        print(f"   ID: {admin.id}")
        print(f"   Email: admin@smartmatch.pro")
        print(f"   Password: Admin123!@#")
        print(f"   is_superuser: {admin.is_superuser}")

        return admin


if __name__ == "__main__":
    try:
        admin = asyncio.run(create_admin())
        print("\n" + "=" * 50)
        print("🎉 Admin prêt à l'emploi !")
        print("=" * 50)
        print("\nPour tester les routes admin:")
        print("1. Login avec admin@smartmatch.pro / Admin123!@#")
        print("2. Utiliser le token JWT dans Swagger UI")
        print("3. Tester les routes:")
        print("   • GET /api/v1/users/ (list all users)")
        print("   • GET /api/v1/profiles/ (list all profiles)")
        print("   • DELETE /api/v1/storage/{file_path}")
        print("   • DELETE /api/v1/users/{id}")

    except Exception as e:
        print(f"\n❌ Erreur: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)