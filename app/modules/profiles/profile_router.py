# app/modules/profiles/profile_router.py

"""
Profile router with REST endpoints.
"""

from uuid import UUID
from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.dependencies import get_db, get_current_user, get_current_admin_user
from app.modules.users.user_model import User, Profile
from app.modules.profiles.profile_schema import (
    ProfileCreate,
    ProfileUpdate,
    ProfileResponse,
    ProfileListResponse,
)
from app.modules.profiles.profile_service import ProfileService
from app.core.exceptions import NotFoundException, ConflictException


router = APIRouter(prefix="/profiles", tags=["Profiles"])


@router.post("/", response_model=ProfileResponse, status_code=status.HTTP_201_CREATED)
def create_profile(
    profile_data: ProfileCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Create a profile for the authenticated user.
    """
    service = ProfileService(db)
    
    # Vérifier si un profil existe déjà
    existing = service.get_profile_by_user_id(current_user.id)
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Profile already exists for this user"
        )
    
    # Créer le profil avec les données
    profile = Profile(
        user_id=current_user.id,
        first_name=profile_data.full_name.split()[0] if profile_data.full_name else None,
        last_name=" ".join(profile_data.full_name.split()[1:]) if profile_data.full_name and len(profile_data.full_name.split()) > 1 else "",
        title=profile_data.title,
        bio=profile_data.bio,
        location=profile_data.location,
        phone=profile_data.phone,
        linkedin_url=str(profile_data.linkedin_url) if profile_data.linkedin_url else None,
        experience_years=profile_data.experience_years,
        education_level=profile_data.education_level.value if profile_data.education_level else None,
    )
    
    db.add(profile)
    db.commit()
    db.refresh(profile)
    
    return profile


@router.get("/me", response_model=ProfileResponse)
def get_my_profile(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Get the profile of the authenticated user.
    """
    service = ProfileService(db)
    profile = service.get_profile_by_user_id(current_user.id)
    
    if not profile:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Profile not found for this user"
        )
    
    return profile


@router.get("/{profile_id}", response_model=ProfileResponse)
def get_profile_by_id(
    profile_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Get a profile by ID.
    """
    service = ProfileService(db)
    profile = service.get_profile_by_id(profile_id)
    
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


@router.put("/{profile_id}", response_model=ProfileResponse)
def update_profile(
    profile_id: int,
    profile_data: ProfileUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Update a profile.
    """
    service = ProfileService(db)
    profile = service.get_profile_by_id(profile_id)
    
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
    
    # Mise à jour des champs
    if profile_data.full_name is not None:
        parts = profile_data.full_name.split()
        profile.first_name = parts[0] if parts else None
        profile.last_name = " ".join(parts[1:]) if len(parts) > 1 else ""
    
    if profile_data.title is not None:
        profile.title = profile_data.title
    
    if profile_data.bio is not None:
        profile.bio = profile_data.bio
    
    if profile_data.location is not None:
        profile.location = profile_data.location
    
    if profile_data.phone is not None:
        profile.phone = profile_data.phone
    
    if profile_data.linkedin_url is not None:
        profile.linkedin_url = str(profile_data.linkedin_url)
    
    if profile_data.experience_years is not None:
        profile.experience_years = profile_data.experience_years
    
    if profile_data.education_level is not None:
        profile.education_level = profile_data.education_level.value
    
    if profile_data.status is not None:
        profile.status = profile_data.status.value
    
    if profile_data.skills_raw is not None:
        profile.skills_raw = profile_data.skills_raw
    
    if profile_data.skills_extracted is not None:
        profile.skills_extracted = profile_data.skills_extracted
    
    db.commit()
    db.refresh(profile)
    
    return profile


@router.get("/", response_model=ProfileListResponse)
def list_profiles(
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    current_user: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db),
):
    """
    List all profiles (admin only).
    """
    service = ProfileService(db)
    profiles, total = service.get_all_profiles(page=page, limit=limit)
    
    pages = (total + limit - 1) // limit
    
    return ProfileListResponse(
        items=profiles,
        total=total,
        page=page,
        limit=limit,
        pages=pages,
    )


@router.get("/search/by-skill", response_model=ProfileListResponse)
def search_profiles_by_skill(
    skill: str = Query(..., min_length=1, description="Skill to search for"),
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Search profiles by extracted skill.
    """
    service = ProfileService(db)
    profiles, total = service.search_profiles_by_skill(skill=skill, page=page, limit=limit)
    
    pages = (total + limit - 1) // limit
    
    return ProfileListResponse(
        items=profiles,
        total=total,
        page=page,
        limit=limit,
        pages=pages,
    )


@router.delete("/{profile_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_profile(
    profile_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Delete a profile.
    """
    service = ProfileService(db)
    profile = service.get_profile_by_id(profile_id)
    
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
    
    db.delete(profile)
    db.commit()