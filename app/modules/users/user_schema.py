from typing import List, Optional
from datetime import datetime
from pydantic import BaseModel, EmailStr, ConfigDict, model_validator

from app.modules.auth.auth_schema import RegisterRequest


class UserCreate(RegisterRequest):
    pass


class UserUpdate(BaseModel):
    """Schéma de mise à jour incluant les champs User et Profile."""
    email: Optional[EmailStr] = None
    full_name: Optional[str] = None
    bio: Optional[str] = None
    phone: Optional[str] = None
    location: Optional[str] = None


class UserResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    email: EmailStr
    is_superuser: bool
    is_active: bool
    created_at: datetime
    full_name: Optional[str] = None

    @model_validator(mode="before")
    @classmethod
    def extract_full_name_from_profile(cls, data):
        """
        Récupère full_name depuis user.profile SANS déclencher de lazy load.
        Lit uniquement __dict__ (données déjà chargées en mémoire).
        """
        if not hasattr(data, "__dict__"):
            return data

        # full_name déjà présent sur l'objet User
        if data.__dict__.get("full_name") is not None:
            return data

        # Lire le profile depuis __dict__ seulement (pas de lazy load)
        profile = data.__dict__.get("profile")

        if profile is not None:
            full_name = getattr(profile, "full_name", None)
            if full_name:
                data.__dict__["full_name"] = full_name

        return data


class UserListResponse(BaseModel):
    items: List[UserResponse]
    total: int
    page: int
    limit: int