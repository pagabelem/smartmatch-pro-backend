# app/modules/skill_gap/skill_gap_schema.py

from datetime import datetime
from typing import List
from pydantic import BaseModel, Field


class SkillGapResponse(BaseModel):
    """Résultat de l'analyse skill gap pour un profil/offre."""
    id: int
    user_id: int
    job_id: int
    matching_skills: List[str]
    missing_skills: List[str]
    extra_skills: List[str]
    coverage_percent: int = Field(..., ge=0, le=100)
    created_at: datetime

    model_config = {"from_attributes": True}


class SkillGapSummary(BaseModel):
    """Résumé global du skill gap d'un utilisateur sur toutes les offres."""
    user_id: int
    total_jobs_analyzed: int
    average_coverage_percent: int
    top_missing_skills: List[str]
    message: str


class SkillGapListResponse(BaseModel):
    """Liste paginée de skill gaps."""
    items: List[SkillGapResponse]
    total: int
    page: int
    page_size: int
    pages: int
    has_next: bool
    has_prev: bool