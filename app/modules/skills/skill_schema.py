"""
skills/skill_schema.py — Pydantic v2 schemas for the Skills module.

Schemas
-------
  SkillBase        Common fields (name, display_name, category, skill_type)
  SkillCreate      Input for POST /skills
  SkillUpdate      Input for PUT /skills/{id}  (all fields optional)
  SkillResponse    Output — full skill object returned by the API
  SkillListResponse Paginated list response
"""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field, field_validator

from app.shared.enums import SkillCategory, SkillType
from app.shared.utils import normalize_skill


# ── Base ──────────────────────────────────────────────────────────────────────
class SkillBase(BaseModel):
    name: str = Field(
        ...,
        min_length=2,
        max_length=100,
        description="Normalised skill name (lowercase). E.g. 'python'.",
        examples=["python"],
    )
    display_name: str | None = Field(
        default=None,
        max_length=100,
        description="Human-readable display name. Defaults to title-cased `name`.",
        examples=["Python"],
    )
    category: SkillCategory | None = Field(
        default=None,
        description="Skill sub-domain category.",
    )
    skill_type: SkillType = Field(
        default=SkillType.HARD,
        description="'hard' for technical skills, 'soft' for interpersonal skills.",
    )

    @field_validator("name")
    @classmethod
    def normalise_name(cls, v: str) -> str:
        """Always store the name in normalised lowercase form."""
        return normalize_skill(v)

    @field_validator("display_name", mode="before")
    @classmethod
    def default_display_name(cls, v, info) -> str | None:
        """If display_name is not provided, derive it from name."""
        return v  # populated by SkillCreate validator below if None


# ── Create ────────────────────────────────────────────────────────────────────
class SkillCreate(SkillBase):
    """Input schema for POST /skills."""

    @field_validator("display_name", mode="before")
    @classmethod
    def default_display_name(cls, v, info) -> str:
        """If display_name is absent, title-case the name."""
        if not v:
            # info.data may not have 'name' yet in v2 — safe fallback
            return v or ""
        return v

    def model_post_init(self, __context) -> None:
        """Ensure display_name always has a value after model creation."""
        if not self.display_name:
            self.display_name = self.name.title()


# ── Update ────────────────────────────────────────────────────────────────────
class SkillUpdate(BaseModel):
    """Input schema for PUT /skills/{id}. All fields optional."""

    name: str | None = Field(
        default=None,
        min_length=2,
        max_length=100,
    )
    display_name: str | None = Field(
        default=None,
        max_length=100,
    )
    category: SkillCategory | None = None
    skill_type: SkillType | None = None

    @field_validator("name")
    @classmethod
    def normalise_name(cls, v: str | None) -> str | None:
        return normalize_skill(v) if v else None


# ── Response ──────────────────────────────────────────────────────────────────
class SkillResponse(BaseModel):
    """Full skill object returned by the API."""

    id:           int
    name:         str
    display_name: str
    category:     SkillCategory | None = None
    skill_type:   SkillType
    created_at:   datetime

    model_config = {"from_attributes": True}


class SkillListResponse(BaseModel):
    """Wrapper used by the paginated GET /skills endpoint."""

    items:     list[SkillResponse]
    total:     int
    page:      int
    page_size: int
    pages:     int
    has_next:  bool
    has_prev:  bool
