from typing import Annotated
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.modules.auth.auth_service import get_current_user_from_token
from app.modules.users.user_model import User

# ✅ Standardisation sur HTTPBearer : simple, robuste et parfaitement intercepté par pytest
security = HTTPBearer(auto_error=False)


async def get_current_user(
    bearer: HTTPAuthorizationCredentials | None = Depends(security),
    db: AsyncSession = Depends(get_db),
) -> User:
    """
    Récupère l'utilisateur courant à partir du token JWT Bearer.
    Lève immédiatement une exception 401 si le token est manquant ou invalide.
    """
    if not bearer:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated. Missing token.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    token = bearer.credentials
    user = await get_current_user_from_token(db, token)
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials or expired token.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    return user


async def get_current_active_user(
    current_user: Annotated[User, Depends(get_current_user)],
) -> User:
    """
    Vérifie que l'utilisateur récupéré est actif.
    """
    if not current_user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Inactive user account.",
        )
    
    return current_user


async def get_current_superuser(
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: AsyncSession = Depends(get_db),
) -> User:
    """
    Vérifie de manière stricte si l'utilisateur est un superadmin.
    Effectue un re-fetch en BDD pour éviter les problèmes de cache d'état en cours de test.
    """
    # Élimine le problème de désynchronisation de l'attribut is_superuser pendant les tests
    await db.refresh(current_user)
    
    if not current_user.is_superuser:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions. Superuser access required.",
        )
    
    return current_user