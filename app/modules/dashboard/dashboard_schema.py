# app/modules/dashboard/dashboard_schema.py

from typing import List, Optional
from pydantic import BaseModel


class JobStats(BaseModel):
    """Statistiques sur les offres d'emploi."""
    total_active: int
    total_expired: int
    total_draft: int
    top_locations: List[dict]
    top_contract_types: List[dict]


class ProfileStats(BaseModel):
    """Statistiques sur le profil de l'utilisateur."""
    has_profile: bool
    total_skills: int
    top_skills: List[str]
    experience_years: Optional[int] = None
    education_level: Optional[str] = None


class MatchingStats(BaseModel):
    """Statistiques sur le matching de l'utilisateur."""
    total_recommendations: int
    average_score: float
    top_score: float
    excellent_count: int
    good_count: int
    average_count: int
    low_count: int


class SkillGapStats(BaseModel):
    """Statistiques sur le skill gap de l'utilisateur."""
    total_analyses: int
    average_coverage_percent: int
    top_missing_skills: List[str]


class DashboardStats(BaseModel):
    """Tableau de bord complet d'un utilisateur."""
    user_id: int
    profile: ProfileStats
    jobs: JobStats
    matching: MatchingStats
    skill_gap: SkillGapStats


class MarketTrend(BaseModel):
    """Tendance du marché pour une compétence."""
    skill: str
    demand_count: int


class MarketTrendsResponse(BaseModel):
    """Tendances globales du marché de l'emploi."""
    top_demanded_skills: List[MarketTrend]
    total_active_jobs: int
    top_locations: List[dict]
    top_contract_types: List[dict]