from app.database import SessionLocal 
from app.modules.users.user_model import User 
 
print("Recherche de l'utilisateur test@example.com...") 
db = SessionLocal() 
user = db.query(User).filter(User.email == "test@example.com").first() 
if user: 
    user.is_superuser = True 
    db.commit() 
    print(f"✅ {user.email} est maintenant admin (superuser=True)") 
else: 
    print("❌ Utilisateur test@example.com non trouvé") 
    print("Création d'un nouvel admin...") 
    from app.core.security import get_password_hash 
    new_admin = User( 
        email="admin@example.com", 
        hashed_password=get_password_hash("Admin123!@#"), 
        is_superuser=True, 
        is_active=True, 
    ) 
    db.add(new_admin) 
    db.commit() 
    print(f"✅ Admin admin@example.com créé") 
db.close() 
