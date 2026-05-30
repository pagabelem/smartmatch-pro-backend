from typing import Optional, List
from sqlalchemy.orm import Session
from app.modules.users.user_model import User
from app.modules.users.user_schema import UserUpdate


class UserService:
    def __init__(self, db: Session):
        self.db = db
    
    def get_user_by_id(self, user_id: int) -> Optional[User]:
        """Récupère un utilisateur par son ID"""
        return self.db.query(User).filter(User.id == user_id).first()
    
    def get_user_by_email(self, email: str) -> Optional[User]:
        """Récupère un utilisateur par son email"""
        return self.db.query(User).filter(User.email == email).first()
    
    def get_all_users(self, page: int = 1, limit: int = 20) -> tuple[List[User], int]:
        """Récupère tous les utilisateurs avec pagination"""
        offset = (page - 1) * limit
        
        total = self.db.query(User).count()
        users = self.db.query(User).order_by(User.created_at.desc()).offset(offset).limit(limit).all()
        
        return users, total
    
    def update_user(self, user_id: int, user_update: UserUpdate) -> Optional[User]:
        """Met à jour un utilisateur existant (seul email peut être modifié)"""
        user = self.get_user_by_id(user_id)
        if not user:
            return None
        
        update_data = user_update.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            if hasattr(user, field):
                setattr(user, field, value)
        
        self.db.commit()
        self.db.refresh(user)
        return user
    
    def delete_user(self, user_id: int) -> bool:
        """Soft delete : passe is_active à False"""
        user = self.get_user_by_id(user_id)
        if not user:
            return False
        
        user.is_active = False
        self.db.commit()
        return True
    
    def search_users(self, search_term: str, page: int = 1, limit: int = 20) -> tuple[List[User], int]:
        """Recherche des utilisateurs par email"""
        offset = (page - 1) * limit
        search_pattern = f"%{search_term}%"
        
        query = self.db.query(User).filter(User.email.ilike(search_pattern))
        
        total = query.count()
        users = query.order_by(User.created_at.desc()).offset(offset).limit(limit).all()
        
        return users, total