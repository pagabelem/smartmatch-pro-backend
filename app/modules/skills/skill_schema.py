# app/modules/skills/skill_schema.py

from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Field, field_validator

from app.shared.enums import SkillCategory, SkillType
from app.shared.utils import normalize_skill


# ── Schéma de base ─────────────────────────────────────────────────────────────
class SkillBase(BaseModel):
    name: str = Field(
        ...,
        min_length=1,
        max_length=100,
        description="Nom de la compétence (ex: Python, Communication)",
    )
    skill_type: SkillType = Field(
        ...,
        description="Type : 'hard' (technique) ou 'soft' (comportementale)",
    )
    sub_category: Optional[SkillCategory] = Field(
        None,
        description="Sous-domaine optionnel : programming, ai_ml, database…",
    )
    description: Optional[str] = Field(
        None,
        max_length=500,
        description="Description libre de la compétence",
    )

    @field_validator("name")
    @classmethod
    def clean_name(cls, v: str) -> str:
        """Strip les espaces — normalize_skill est appliqué dans le service."""
        return v.strip()


# ── Création ───────────────────────────────────────────────────────────────────
class SkillCreate(SkillBase):
    pass


# ── Mise à jour partielle (tous les champs optionnels) ─────────────────────────
class SkillUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    skill_type: Optional[SkillType] = None
    sub_category: Optional[SkillCategory] = None
    description: Optional[str] = Field(None, max_length=500)
    is_active: Optional[bool] = None

    @field_validator("name")
    @classmethod
    def clean_name(cls, v: Optional[str]) -> Optional[str]:
        return v.strip() if v else v


# ── Réponse complète ───────────────────────────────────────────────────────────
class SkillResponse(SkillBase):
    id: int
    normalized_name: str
    is_active: bool
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


# ── Réponse paginée ────────────────────────────────────────────────────────────
class SkillListResponse(BaseModel):
    total: int
    page: int
    page_size: int
    pages: int
    has_next: bool
    has_prev: bool
    data: List[SkillResponse]


# ── Réponse liste de noms (pour NLP et Matching) ──────────────────────────────
class SkillNamesResponse(BaseModel):
    total: int
    names: List[str]