from app.database import engine, Base
# Import impératif de TOUS les modèles pour que SQLAlchemy les connaisse
from app.modules.users.user_model import User, Profile
from app.modules.auth.auth_model import RefreshToken
from app.modules.skills.skill_model import Skill

def init_tables():
    print("⏳ Connexion à PostgreSQL et création des tables...")
    try:
        # Cette ligne crée les tables uniquement si elles n'existent pas
        Base.metadata.create_all(bind=engine)
        print("✅ Tables créées avec succès (users, profiles, refresh_tokens, skills) !")
    except Exception as e:
        print(f"❌ Erreur lors de la création : {e}")

if __name__ == "__main__":
    init_tables()