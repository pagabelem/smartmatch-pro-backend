from typing import List, Optional
from datetime import datetime
from pydantic import BaseModel, EmailStr, ConfigDict
from app.modules.auth.auth_schema import RegisterRequest


class UserCreate(RegisterRequest):
    pass


class UserUpdate(BaseModel):
    email: Optional[EmailStr] = None
    # full_name n'existe pas dans le modèle, on le retire


class UserResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    
    id: int
    email: EmailStr
    is_superuser: bool
    is_active: bool
    created_at: datetime


class UserListResponse(BaseModel):
    items: List[UserResponse]
    total: int
    page: int
    limit: int