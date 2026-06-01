# app/modules/matching/matching_schema.py

from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, Field
from app.shared.enums import MatchScoreLabel


class RecommendationResponse(BaseModel):
    """Un résultat de matching retourné par l'API."""
    id: int
    user_id: int
    job_id: int
    score: float = Field(..., ge=0.0, le=1.0)
    score_label: str
    created_at: datetime

    model_config = {"from_attributes": True}


class MatchingRunResponse(BaseModel):
    """Réponse après un calcul de matching complet."""
    user_id: int
    total_jobs_evaluated: int
    recommendations_saved: int
    top_score: float
    message: str


class RecommendationListResponse(BaseModel):
    """Liste paginée de recommandations."""
    items: List[RecommendationResponse]
    total: int
    page: int
    page_size: int
    pages: int
    has_next: bool
    has_prev: bool