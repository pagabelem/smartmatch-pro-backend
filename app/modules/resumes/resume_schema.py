"""
app/modules/resumes/resume_schema.py
Schémas Pydantic v2 pour le module Resumes.
"""

from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, Field, ConfigDict


class ResumeUploadResponse(BaseModel):
    """Réponse minimale après upload d'un CV."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    filename: str
    file_path: str  # ✅ AJOUTÉ
    file_size: int = Field(..., description="Taille du fichier en octets")
    is_parsed: bool
    created_at: datetime


class ResumeResponse(ResumeUploadResponse):
    """Réponse complète incluant le texte extrait et le chemin."""

    raw_text: Optional[str] = None
    mime_type: str
    profile_id: int
    updated_at: datetime


class ResumeListResponse(BaseModel):
    """Réponse paginée pour la liste des CVs d'un profil."""

    items: List[ResumeResponse]
    total: int
    page: int
    limit: int
    pages: int


class ResumeTextResponse(BaseModel):
    """Réponse pour l'endpoint /text."""

    id: int
    filename: str
    is_parsed: bool
    raw_text: Optional[str] = None