from typing import List
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from app.dependencies import get_db, get_current_user
from app.modules.users.user_model import User as UserModel
from app.modules.users.user_schema import (
    UserResponse, 
    UserUpdate, 
    UserListResponse
)
from app.modules.users.user_service import UserService


router = APIRouter(tags=["users"])


@router.get("/", response_model=UserListResponse)
def get_all_users(
    page: int = Query(1, ge=1, description="Numéro de la page"),
    limit: int = Query(20, ge=1, le=100, description="Nombre d'items par page"),
    current_user: UserModel = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Récupère tous les utilisateurs (admin uniquement)
    """
    if not current_user.is_superuser:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Accès réservé aux administrateurs"
        )
    
    user_service = UserService(db)
    users, total = user_service.get_all_users(page=page, limit=limit)
    
    return UserListResponse(
        items=[UserResponse.model_validate(user) for user in users],
        total=total,
        page=page,
        limit=limit
    )


@router.get("/me", response_model=UserResponse)
def get_current_user_info(
    current_user: UserModel = Depends(get_current_user)
):
    """
    Récupère les informations de l'utilisateur connecté
    """
    return UserResponse.model_validate(current_user)


@router.get("/search", response_model=UserListResponse)
def search_users(
    q: str = Query(..., min_length=1, description="Terme de recherche"),
    page: int = Query(1, ge=1, description="Numéro de la page"),
    limit: int = Query(20, ge=1, le=100, description="Nombre d'items par page"),
    current_user: UserModel = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Recherche des utilisateurs par email
    """
    user_service = UserService(db)
    users, total = user_service.search_users(
        search_term=q, 
        page=page, 
        limit=limit
    )
    
    return UserListResponse(
        items=[UserResponse.model_validate(user) for user in users],
        total=total,
        page=page,
        limit=limit
    )


@router.get("/{user_id}", response_model=UserResponse)
def get_user_by_id(
    user_id: int,
    current_user: UserModel = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Récupère un utilisateur par son ID
    """
    user_service = UserService(db)
    user = user_service.get_user_by_id(user_id)
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Utilisateur non trouvé"
        )
    
    if current_user.id != user_id and not current_user.is_superuser:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Accès non autorisé"
        )
    
    return UserResponse.model_validate(user)


@router.put("/{user_id}", response_model=UserResponse)
def update_user(
    user_id: int,
    user_update: UserUpdate,
    current_user: UserModel = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Met à jour un utilisateur (seul l'email peut être modifié)
    """
    if current_user.id != user_id and not current_user.is_superuser:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Vous ne pouvez modifier que vos propres informations"
        )
    
    user_service = UserService(db)
    user = user_service.update_user(user_id, user_update)
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Utilisateur non trouvé"
        )
    
    return UserResponse.model_validate(user)


@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_user(
    user_id: int,
    current_user: UserModel = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Soft delete d'un utilisateur (admin uniquement)
    """
    if not current_user.is_superuser:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Seuls les administrateurs peuvent supprimer des utilisateurs"
        )
    
    if current_user.id == user_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Vous ne pouvez pas vous supprimer vous-même"
        )
    
    user_service = UserService(db)
    deleted = user_service.delete_user(user_id)
    
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Utilisateur non trouvé"
        )