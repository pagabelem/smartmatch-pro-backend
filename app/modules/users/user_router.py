from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Dict, Any
from app.database import get_db

from app.modules.auth.dependencies import get_current_active_user, get_current_superuser
from app.modules.users.user_model import User
from app.modules.users.user_schema import UserResponse, UserUpdate
from app.modules.users.user_service import UserService

router = APIRouter(prefix="/users", tags=["Users"])


@router.get("/me", response_model=UserResponse)
async def get_current_user_info(
    current_user: User = Depends(get_current_active_user),
):
    """Récupère les informations de l'utilisateur connecté."""
    return UserResponse.model_validate(current_user)


@router.get("/search", response_model=Dict[str, Any])
async def search_users(
    email: str = Query(None),
    limit: int = Query(10),
    offset: int = Query(0),
    current_user: User = Depends(get_current_superuser),
    db: AsyncSession = Depends(get_db),
):
    """Recherche des utilisateurs (admin uniquement)."""
    user_service = UserService(db)
    users, total = await user_service.search_users(email=email, limit=limit, offset=offset)
    return {
        "users": [UserResponse.model_validate(u) for u in users],
        "total": total,
    }


@router.get("", response_model=Dict[str, Any])
async def list_users(
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1),
    current_user: User = Depends(get_current_superuser),
    db: AsyncSession = Depends(get_db),
):
    """Récupère la liste de tous les utilisateurs (admin uniquement)."""
    user_service = UserService(db)
    users, total = await user_service.get_all_users(page=page, limit=limit)
    return {
        "users": [UserResponse.model_validate(u) for u in users],
        "total": total,
    }


@router.get("/{user_id}", response_model=UserResponse)
async def get_user_by_id(
    user_id: int,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """Récupère un utilisateur spécifique par son ID."""
    if current_user.id != user_id and not current_user.is_superuser:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Vous n'êtes pas autorisé à voir ce profil.",
        )
    user_service = UserService(db)
    user = await user_service.get_user_by_id(user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Utilisateur non trouvé.",
        )
    return UserResponse.model_validate(user)


@router.put("/{user_id}", response_model=UserResponse)
async def update_user(
    user_id: int,
    payload: UserUpdate,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """Met à jour un utilisateur."""
    if current_user.id != user_id and not current_user.is_superuser:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Vous n'êtes pas autorisé à modifier cet utilisateur.",
        )
    user_service = UserService(db)
    updated_user = await user_service.update_user(user_id, payload)
    if not updated_user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Utilisateur non trouvé.",
        )
    return UserResponse.model_validate(updated_user)


@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_user(
    user_id: int,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """Supprime (soft delete) un utilisateur."""
    if current_user.id != user_id and not current_user.is_superuser:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Action interdite.",
        )
    user_service = UserService(db)
    success = await user_service.delete_user(user_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Utilisateur non trouvé.",
        )
    return None