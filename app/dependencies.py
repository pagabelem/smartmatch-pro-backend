from typing import AsyncGenerator, Annotated, Optional
from fastapi import Depends
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db as get_async_db
from app.core.exceptions import UnauthorizedException, ForbiddenException
from app.modules.users.user_model import User
from app.modules.auth.auth_service import get_current_user_from_token

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login", auto_error=False)

async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async for session in get_async_db():
        yield session

async def get_current_user(
    db: AsyncSession = Depends(get_db),
    token: Optional[str] = Depends(oauth2_scheme),
) -> User:
    if not token:
        raise UnauthorizedException("Not authenticated")
        
    user = await get_current_user_from_token(db, token)
    if not user:
        raise UnauthorizedException("Could not validate credentials")
    
    # Remplacé 'refresh' par une simple vérification d'état si nécessaire.
    # Dans 99% des cas, si l'utilisateur est retourné par le service, il est valide.
    return user

async def get_current_active_user(
    current_user: User = Depends(get_current_user)
) -> User:
    # Utilisation explicite de l'attribut is_active
    if not current_user.is_active:
        raise UnauthorizedException("Account is deactivated.")
    return current_user

async def get_current_admin_user(
    current_user: User = Depends(get_current_active_user)
) -> User:
    if not current_user.is_superuser:
        raise ForbiddenException("Admin access required.")
    return current_user

# Alias propres pour les routes
CurrentUser = Annotated[User, Depends(get_current_active_user)]
AdminUser = Annotated[User, Depends(get_current_admin_user)]

# Simplification totale pour le superuser
async def get_current_superuser(user: AdminUser) -> User:
    return user