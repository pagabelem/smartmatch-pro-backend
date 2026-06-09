"""
Profile router with REST endpoints.
"""

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.modules.auth.dependencies import get_current_active_user, get_current_superuser
from app.modules.users.user_model import User, Profile
from app.modules.profiles.profile_schema import (
    ProfileCreate,
    ProfileUpdate,
    ProfileResponse,
    ProfileListResponse,
)
from app.modules.profiles.profile_service import ProfileService


# ✅ Définition du router avec gestion propre du prefix
router = APIRouter(prefix="/profiles", tags=["Profiles"])


@router.post("/", response_model=ProfileResponse, status_code=status.HTTP_201_CREATED)
async def create_profile(
    profile_data: ProfileCreate,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """Create a profile for the authenticated user."""
    service = ProfileService(db)

    existing = await service.get_profile_by_user_id(current_user.id)
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Profile already exists for this user"
        )

    # Extraire les données du schéma Pydantic
    profile_dict = profile_data.model_dump(exclude_unset=True)

    # 🛡️ SÉCURITÉ ROBUSTE : Supprimer les paramètres de schéma non supportés par le modèle ORM
    profile_dict.pop("title", None)
    profile_dict.pop("experience_years", None)  # 🔥 FIX : Empêche le plantage sur Profile()

    # Gestion de la conversion full_name -> first/last name
    if 'full_name' in profile_dict and profile_dict['full_name']:
        parts = profile_dict['full_name'].split()
        profile_dict['first_name'] = parts[0] if parts else None
        profile_dict['last_name'] = ' '.join(parts[1:]) if len(parts) > 1 else ""
        del profile_dict['full_name']

    # Instanciation désormais 100% saine pour SQLAlchemy
    profile = Profile(user_id=current_user.id, **profile_dict)

    db.add(profile)
    await db.commit()
    await db.refresh(profile)

    return profile


@router.get("/me", response_model=ProfileResponse)
async def get_my_profile(
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """Get the profile of the authenticated user."""
    service = ProfileService(db)
    profile = await service.get_profile_by_user_id(current_user.id)

    if not profile:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Profile not found for this user"
        )

    return profile


@router.get("/{profile_id}", response_model=ProfileResponse)
async def get_profile_by_id(
    profile_id: int,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """Get a profile by ID."""
    service = ProfileService(db)
    profile = await service.get_profile_by_id(profile_id)

    if not profile:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Profile not found"
        )

    if profile.user_id != current_user.id and not current_user.is_superuser:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to view this profile"
        )

    return profile


# ✅ AJOUT : Route GET / pour lister tous les profils (admin only)
@router.get("/", response_model=ProfileListResponse)
async def list_profiles(
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    current_user: User = Depends(get_current_superuser),
    db: AsyncSession = Depends(get_db),
):
    """List all profiles (admin only)."""
    service = ProfileService(db)
    profiles = await service.get_profiles_paginated(page=page, limit=limit)
    total = await service.count_profiles()

    return {
        "items": profiles,
        "total": total,
        "page": page,
        "limit": limit,
        "pages": (total + limit - 1) // limit,
    }


@router.put("/{profile_id}", response_model=ProfileResponse)
async def update_profile(
    profile_id: int,
    profile_data: ProfileUpdate,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """Update a profile."""
    service = ProfileService(db)
    profile = await service.get_profile_by_id(profile_id)

    if not profile:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Profile not found"
        )

    if profile.user_id != current_user.id and not current_user.is_superuser:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to update this profile"
        )

    update_data = profile_data.model_dump(exclude_unset=True)
    update_data.pop("title", None)             # 🛡️ Sécurité additionnelle sur le PUT
    update_data.pop("experience_years", None)  # 🔥 FIX : Évite aussi les crashs sur la mise à jour

    if 'full_name' in update_data and update_data['full_name']:
        parts = update_data['full_name'].split()
        update_data['first_name'] = parts[0] if parts else None
        update_data['last_name'] = ' '.join(parts[1:]) if len(parts) > 1 else ""
        del update_data['full_name']

    for field, value in update_data.items():
        if hasattr(profile, field):
            setattr(profile, field, value)

    await db.commit()
    await db.refresh(profile)

    return profile


@router.delete("/{profile_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_profile(
    profile_id: int,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """Delete a profile."""
    service = ProfileService(db)
    profile = await service.get_profile_by_id(profile_id)

    if not profile:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Profile not found"
        )

    if profile.user_id != current_user.id and not current_user.is_superuser:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to delete this profile"
        )

    await db.delete(profile)
    await db.commit()