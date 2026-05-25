"""
Profile service for business logic operations.
"""

from typing import Optional, List, Tuple
from uuid import UUID
from sqlalchemy.orm import Session
from sqlalchemy import or_

from app.modules.users.user_model import User, Profile  # ← Changé: import depuis user_model
from app.modules.profiles.profile_schema import ProfileCreate, ProfileUpdate
from app.core.exceptions import NotFoundException, ConflictException


class ProfileService:
    """Service class for profile management."""
    
    def __init__(self, db: Session):
        self.db = db
    
    def create_profile(self, user_id: int, profile_data: ProfileCreate) -> Profile:
        """Create a new profile for a user."""
        # Check if profile already exists for this user
        existing = self.db.query(Profile).filter(Profile.user_id == user_id).first()
        if existing:
            raise ConflictException(f"Profile already exists for user {user_id}")
        
        profile = Profile(
            user_id=user_id,
            first_name=profile_data.first_name,
            last_name=profile_data.last_name,
            bio=profile_data.bio,
            phone=profile_data.phone,
            location=profile_data.location,
            linkedin_url=profile_data.linkedin_url,
            github_url=profile_data.github_url,
            degree=profile_data.degree,
            field_of_study=profile_data.field_of_study,
            school=profile_data.school,
            graduation_year=profile_data.graduation_year,
            skills_raw=profile_data.skills_raw,
            target_job_title=profile_data.target_job_title,
            target_sectors=profile_data.target_sectors,
            target_contract_types=profile_data.target_contract_types,
        )
        
        self.db.add(profile)
        self.db.commit()
        self.db.refresh(profile)
        return profile
    
    def get_profile_by_id(self, profile_id: int) -> Optional[Profile]:
        """Get profile by ID."""
        return self.db.query(Profile).filter(Profile.id == profile_id).first()
    
    def get_profile_by_user_id(self, user_id: int) -> Optional[Profile]:
        """Get profile by user ID."""
        return self.db.query(Profile).filter(Profile.user_id == user_id).first()
    
    def update_profile(self, profile_id: int, profile_data: ProfileUpdate) -> Profile:
        """Update an existing profile."""
        profile = self.get_profile_by_id(profile_id)
        if not profile:
            raise NotFoundException("Profile", profile_id)
        
        update_data = profile_data.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            if hasattr(profile, field):
                setattr(profile, field, value)
        
        self.db.commit()
        self.db.refresh(profile)
        return profile
    
    def update_skills_extracted(self, profile_id: int, skills: dict) -> Profile:
        """Update extracted skills for a profile (called by NLP module)."""
        profile = self.get_profile_by_id(profile_id)
        if not profile:
            raise NotFoundException("Profile", profile_id)
        
        profile.skills_extracted = skills
        
        self.db.commit()
        self.db.refresh(profile)
        return profile
    
    def get_all_profiles(
        self, 
        page: int = 1, 
        limit: int = 20,
        status: Optional[str] = None
    ) -> Tuple[List[Profile], int]:
        """Get all profiles with pagination."""
        query = self.db.query(Profile)
        
        # Note: status filter would need a status column in Profile
        # For now, just get all
        
        total = query.count()
        offset = (page - 1) * limit
        profiles = query.order_by(Profile.created_at.desc()).offset(offset).limit(limit).all()
        
        return profiles, total
    
    def search_profiles_by_skill(
        self, 
        skill: str, 
        page: int = 1, 
        limit: int = 20
    ) -> Tuple[List[Profile], int]:
        """Search profiles by skill (case-insensitive)."""
        skill_lower = skill.lower()
        
        all_profiles = self.db.query(Profile).all()
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
    
    def delete_profile(self, profile_id: int) -> bool:
        """Delete profile."""
        profile = self.get_profile_by_id(profile_id)
        if not profile:
            return False
        
        self.db.delete(profile)
        self.db.commit()
        return True