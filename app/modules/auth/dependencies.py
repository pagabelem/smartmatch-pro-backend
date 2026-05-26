# app/modules/auth/dependencies.py

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.modules.auth.auth_service import get_current_user_from_token
from app.modules.users.user_model import User

security = HTTPBearer()


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: AsyncSession = Depends(get_db),
) -> User:
    """
    Récupère l'utilisateur courant à partir du token JWT.
    
    Args:
        credentials: Les credentials HTTP Bearer contenant le token
        db: Session asynchrone de la base de données
    
    Returns:
        User: L'utilisateur authentifié
    
    Raises:
        HTTPException: Si le token est invalide ou l'utilisateur inexistant
    """
    token = credentials.credentials
    
    # Délègue la validation du token et la récupération de l'utilisateur au service
    user = await get_current_user_from_token(db, token)
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    return user