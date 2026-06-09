"""
Profile service for business logic operations.
"""

import asyncio
from typing import Optional, List, Tuple
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, or_, func
from sqlalchemy.orm import selectinload

from app.modules.users.user_model import User, Profile
from app.modules.profiles.profile_schema import ProfileCreate, ProfileUpdate
from app.core.exceptions import NotFoundException, ConflictException


class ProfileService:
    """Service class for profile management (ASYNC & SYNC compliant version)."""

    def __init__(self, db: AsyncSession):
        self.db = db

    def _is_async(self) -> bool:
        """Vérifie si la session actuelle requiert des appels asynchrones."""
        return hasattr(self.db, "execute_with_context") or asyncio.iscoroutinefunction(self.db.execute)

    async def create_profile(self, user_id: int, profile_data: ProfileCreate) -> Profile:
        """Create a new profile for a user."""
        # Check if profile already exists for this user
        existing = await self.get_profile_by_user_id(user_id)
        if existing:
            raise ConflictException(f"Profile already exists for user {user_id}")

        # Convert Pydantic model to dict
        profile_dict = profile_data.model_dump(exclude_unset=True)

        # Handle full_name if provided (split into first_name/last_name)
        if 'full_name' in profile_dict and profile_dict['full_name']:
            parts = profile_dict['full_name'].split()
            profile_dict['first_name'] = parts[0] if parts else None
            profile_dict['last_name'] = ' '.join(parts[1:]) if len(parts) > 1 else ""
            del profile_dict['full_name']

        profile = Profile(user_id=user_id, **profile_dict)

        self.db.add(profile)
        await self.db.commit()
        if self._is_async():
            await self.db.refresh(profile)
        else:
            self.db.refresh(profile)
        return profile

    async def get_profile_by_id(self, profile_id: int) -> Optional[Profile]:
        """Get profile by ID."""
        stmt = select(Profile).where(Profile.id == profile_id)
        if self._is_async():
            result = await self.db.execute(stmt)
        else:
            result = self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def get_profile_by_user_id(self, user_id: int) -> Optional[Profile]:
        """Get profile by user ID."""
        stmt = select(Profile).where(Profile.user_id == user_id)
        if self._is_async():
            result = await self.db.execute(stmt)
        else:
            result = self.db.execute(stmt)
        return result.scalar_one_or_none()

    # ✅ AJOUT : Méthodes pour la route GET / (admin only)
    async def get_profiles_paginated(self, page: int = 1, limit: int = 20) -> List[Profile]:
        """Get all profiles with pagination."""
        offset = (page - 1) * limit
        stmt = select(Profile).order_by(Profile.created_at.desc()).offset(offset).limit(limit)

        if self._is_async():
            result = await self.db.execute(stmt)
        else:
            result = self.db.execute(stmt)
        return result.scalars().all()

    async def count_profiles(self) -> int:
        """Count total number of profiles."""
        stmt = select(func.count()).select_from(Profile)

        if self._is_async():
            result = await self.db.execute(stmt)
        else:
            result = self.db.execute(stmt)
        return result.scalar()

    async def update_profile(self, profile_id: int, profile_data: ProfileUpdate) -> Profile:
        """Update an existing profile."""
        profile = await self.get_profile_by_id(profile_id)
        if not profile:
            raise NotFoundException("Profile", profile_id)

        update_data = profile_data.model_dump(exclude_unset=True)

        # Handle full_name if provided
        if 'full_name' in update_data and update_data['full_name']:
            parts = update_data['full_name'].split()
            update_data['first_name'] = parts[0] if parts else None
            update_data['last_name'] = ' '.join(parts[1:]) if len(parts) > 1 else ""
            del update_data['full_name']

        for field, value in update_data.items():
            if hasattr(profile, field):
                setattr(profile, field, value)

        await self.db.commit()
        if self._is_async():
            await self.db.refresh(profile)
        else:
            self.db.refresh(profile)
        return profile

    async def update_skills_extracted(self, profile_id: int, skills: dict) -> Profile:
        """Update extracted skills for a profile (called by NLP module)."""
        profile = await self.get_profile_by_id(profile_id)
        if not profile:
            raise NotFoundException("Profile", profile_id)

        profile.skills_extracted = skills

        await self.db.commit()
        if self._is_async():
            await self.db.refresh(profile)
        else:
            self.db.refresh(profile)
        return profile

    async def get_all_profiles(
        self, 
        page: int = 1, 
        limit: int = 20,
        status: Optional[str] = None
    ) -> Tuple[List[Profile], int]:
        """Get all profiles with pagination."""
        query = select(Profile).order_by(Profile.created_at.desc())
        count_query = select(func.count()).select_from(Profile)

        if self._is_async():
            total_result = await self.db.execute(count_query)
            total = total_result.scalar()

            offset = (page - 1) * limit
            result = await self.db.execute(query.offset(offset).limit(limit))
            profiles = result.scalars().all()
        else:
            total_result = self.db.execute(count_query)
            total = total_result.scalar()

            offset = (page - 1) * limit
            result = self.db.execute(query.offset(offset).limit(limit))
            profiles = result.scalars().all()

        return profiles, total

    async def search_profiles_by_skill(
        self, 
        skill: str, 
        page: int = 1, 
        limit: int = 20
    ) -> Tuple[List[Profile], int]:
        """Search profiles by skill (case-insensitive)."""
        skill_lower = skill.lower()
        stmt = select(Profile)

        if self._is_async():
            result = await self.db.execute(stmt)
        else:
            result = self.db.execute(stmt)

        all_profiles = result.scalars().all()

        # Filtrer manuellement (car SQLite JSON n'est pas idéal pour la recherche)
        filtered = []
        for p in all_profiles:
            skills = []
            if p.skills_raw:
                skills.extend(p.skills_raw)
            if p.skills_extracted:
                hard = p.skills_extracted.get("hard_skills", [])
                soft = p.skills_extracted.get("soft_skills", [])
                skills.extend(hard)
                skills.extend(soft)

            if any(skill_lower in str(s).lower() for s in skills):
                filtered.append(p)

        total = len(filtered)
        offset = (page - 1) * limit
        paginated = filtered[offset:offset + limit]

        return paginated, total

    async def search_profiles_by_location(
        self, 
        location: str, 
        page: int = 1, 
        limit: int = 20
    ) -> Tuple[List[Profile], int]:
        """Search profiles by location (case-insensitive)."""
        stmt = select(Profile).where(Profile.location.ilike(f"%{location}%"))

        if self._is_async():
            result = await self.db.execute(stmt)
        else:
            result = self.db.execute(stmt)

        all_profiles = result.scalars().all()

        total = len(all_profiles)
        offset = (page - 1) * limit
        paginated = all_profiles[offset:offset + limit]

        return paginated, total

    async def delete_profile(self, profile_id: int) -> bool:
        """Delete profile."""
        profile = await self.get_profile_by_id(profile_id)
        if not profile:
            return False

        if self._is_async():
            await self.db.delete(profile)
            await self.db.commit()
        else:
            self.db.delete(profile)
            self.db.commit()
        return True