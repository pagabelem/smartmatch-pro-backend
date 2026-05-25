from app.database import SessionLocal 
from app.modules.users.user_model import User 
from app.core.security import get_password_hash 
 
def create_admin(email: str, password: str): 
    db = SessionLocal() 
    existing = db.query(User).filter(User.email == email).first() 
    if existing: 
        existing.is_superuser = True 
        existing.hashed_password = get_password_hash(password) 
        print(f"✅ Utilisateur {email} promu en admin") 
    else: 
        admin = User( 
            email=email, 
            hashed_password=get_password_hash(password), 
            is_superuser=True, 
            is_active=True, 
        ) 
        db.add(admin) 
        print(f"✅ Admin {email} créé") 
    db.commit() 
    db.close() 
 
if __name__ == "__main__": 
    create_admin("admin@example.com", "Admin123!@#") 
