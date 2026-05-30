"""
Profile Pydantic schemas for request/response validation.
"""

from datetime import datetime
from typing import Optional, List, Any
from pydantic import BaseModel, Field, HttpUrl, field_validator, ConfigDict

from app.shared.enums import ProfileStatus, EducationLevel


class ProfileCreate(BaseModel):
    """Schema for creating a new profile."""
    
    full_name: str = Field(..., min_length=2, max_length=255, description="Full name")
    title: Optional[str] = Field(None, max_length=255, description="Desired job title")
    bio: Optional[str] = Field(None, description="Professional biography")
    location: Optional[str] = Field(None, max_length=255, description="City/region")
    phone: Optional[str] = Field(None, pattern=r'^[0-9+\s\-]{10,20}$', description="Phone number")
    linkedin_url: Optional[HttpUrl] = Field(None, description="LinkedIn profile URL")
    experience_years: int = Field(0, ge=0, le=50, description="Years of experience")
    education_level: Optional[EducationLevel] = Field(None, description="Highest education level")
    
    @field_validator("full_name")
    @classmethod
    def validate_full_name(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("Full name cannot be empty")
        return v.strip()


class ProfileUpdate(BaseModel):
    """Schema for updating an existing profile. All fields are optional."""
    
    full_name: Optional[str] = Field(None, min_length=2, max_length=255)
    title: Optional[str] = Field(None, max_length=255)
    bio: Optional[str] = None
    location: Optional[str] = Field(None, max_length=255)
    phone: Optional[str] = Field(None, pattern=r'^[0-9+\s\-]{10,20}$')
    linkedin_url: Optional[HttpUrl] = None
    experience_years: Optional[int] = Field(None, ge=0, le=50)
    education_level: Optional[EducationLevel] = None
    status: Optional[ProfileStatus] = None
    skills_raw: Optional[List[str]] = Field(None, description="List of raw skills")  # ← changé: str → List[str]
    skills_extracted: Optional[dict] = Field(None, description="Extracted skills dictionary")  # ← changé


class ProfileResponse(BaseModel):
    """Schema for profile response (includes all fields)."""
    
    model_config = ConfigDict(from_attributes=True)
    
    id: int  # ← changé: UUID → int
    user_id: int  # ← changé: UUID → int
    full_name: str
    title: Optional[str] = None
    bio: Optional[str] = None
    location: Optional[str] = None
    phone: Optional[str] = None
    linkedin_url: Optional[str] = None
    github_url: Optional[str] = None
    experience_years: int = 0
    education_level: Optional[EducationLevel] = None
    status: ProfileStatus = ProfileStatus.DRAFT
    skills_raw: Optional[List[str]] = None  # ← changé: str → List[str]
    skills_extracted: Optional[dict] = None  # ← changé: List[Any] → dict
    created_at: datetime
    updated_at: datetime


class ProfilePublic(BaseModel):
    """Public profile response (excludes sensitive data)."""
    
    model_config = ConfigDict(from_attributes=True)
    
    id: int  # ← changé: UUID → int
    full_name: str
    title: Optional[str] = None
    location: Optional[str] = None
    experience_years: int = 0
    education_level: Optional[EducationLevel] = None
    skills_extracted: Optional[dict] = None  # ← changé: List[Any] → dict


class ProfileListResponse(BaseModel):
    """Paginated profile list response."""
    
    items: List[ProfileResponse]
    total: int
    page: int
    limit: int
    pages: int


class ProfileSearchRequest(BaseModel):
    """Profile search filters."""
    
    skill: Optional[str] = Field(None, description="Filter by skill")
    location: Optional[str] = Field(None, description="Filter by location")
    experience_min: Optional[int] = Field(None, ge=0, description="Minimum years of experience")
    experience_max: Optional[int] = Field(None, ge=0, description="Maximum years of experience")
    status: Optional[ProfileStatus] = None
    page: int = Field(1, ge=1)
    limit: int = Field(20, ge=1, le=100)