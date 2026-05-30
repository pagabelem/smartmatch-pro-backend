# app/modules/favorites/favorite_schema.py

from datetime import datetime
from typing import Optional

from pydantic import BaseModel

from app.modules.jobs.job_schema import JobResponse


# ── Création ───────────────────────────────────────────────────────────────────
class FavoriteCreate(BaseModel):
    job_id: int


# ── Réponse simple ─────────────────────────────────────────────────────────────
class FavoriteResponse(BaseModel):
    id: int
    user_id: int
    job_id: int
    created_at: datetime

    model_config = {"from_attributes": True}


# ── Réponse enrichie avec détail de l'offre ────────────────────────────────────
class FavoriteWithJobResponse(BaseModel):
    id: int
    user_id: int
    created_at: datetime
    job: Optional[JobResponse] = None

    model_config = {"from_attributes": True}