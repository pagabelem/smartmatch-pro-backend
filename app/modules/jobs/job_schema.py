# app/modules/jobs/job_schema.py

from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Field, field_validator

from app.shared.enums import (
    ContractType,
    DegreeLevel,
    ExperienceLevel,
    ImportSource,
    JobStatus,
    WorkMode,
)
from app.shared.utils import normalize_skill
from app.shared.validators import validate_skills_list


# ── Schéma de base ─────────────────────────────────────────────────────────────
class JobBase(BaseModel):
    title: str = Field(..., min_length=2, max_length=255,
                       description="Intitulé du poste")
    company: str = Field(..., min_length=2, max_length=255,
                         description="Nom de l'entreprise")
    description: Optional[str] = Field(None, description="Description de l'offre")
    location: Optional[str] = Field(None, max_length=255,
                                    description="Ville / pays")
    url: Optional[str] = Field(None, max_length=500,
                               description="Lien vers l'offre originale")
    contract_type: ContractType = Field(
        ContractType.OTHER, description="Type de contrat")
    experience_level: ExperienceLevel = Field(
        ExperienceLevel.ANY, description="Niveau d'expérience requis")
    work_mode: WorkMode = Field(
        WorkMode.ANY, description="Mode de travail")
    degree_level: Optional[DegreeLevel] = Field(
        DegreeLevel.ANY, description="Niveau d'études requis")
    required_skills: List[str] = Field(
        default_factory=list,
        description="Compétences requises (normalisées automatiquement)")
    salary_min: Optional[float] = Field(None, ge=0)
    salary_max: Optional[float] = Field(None, ge=0)
    salary_currency: Optional[str] = Field("DH", max_length=10)
    published_at: Optional[datetime] = None
    expires_at: Optional[datetime] = None

    @field_validator("required_skills")
    @classmethod
    def normalize_skills(cls, skills: List[str]) -> List[str]:
        """Normalise chaque compétence via normalize_skill() de shared/utils."""
        return [normalize_skill(s) for s in skills if s.strip()]

    @field_validator("title", "company")
    @classmethod
    def clean_string(cls, v: str) -> str:
        return v.strip()


# ── Création ───────────────────────────────────────────────────────────────────
class JobCreate(JobBase):
    source: ImportSource = Field(
        ImportSource.MANUAL,
        description="Origine : manual, csv, scraper…")
    status: JobStatus = Field(
        JobStatus.ACTIVE,
        description="Statut initial : active ou draft")


# ── Mise à jour partielle ──────────────────────────────────────────────────────
class JobUpdate(BaseModel):
    title: Optional[str] = Field(None, min_length=2, max_length=255)
    company: Optional[str] = Field(None, min_length=2, max_length=255)
    description: Optional[str] = None
    location: Optional[str] = Field(None, max_length=255)
    url: Optional[str] = Field(None, max_length=500)
    contract_type: Optional[ContractType] = None
    experience_level: Optional[ExperienceLevel] = None
    work_mode: Optional[WorkMode] = None
    degree_level: Optional[DegreeLevel] = None
    required_skills: Optional[List[str]] = None
    salary_min: Optional[float] = Field(None, ge=0)
    salary_max: Optional[float] = Field(None, ge=0)
    salary_currency: Optional[str] = Field(None, max_length=10)
    status: Optional[JobStatus] = None
    published_at: Optional[datetime] = None
    expires_at: Optional[datetime] = None

    @field_validator("required_skills")
    @classmethod
    def normalize_skills(cls, skills: Optional[List[str]]) -> Optional[List[str]]:
        if skills is None:
            return None
        return [normalize_skill(s) for s in skills if s.strip()]


# ── Réponse complète ───────────────────────────────────────────────────────────
class JobResponse(JobBase):
    id: int
    status: JobStatus
    source: ImportSource
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


# ── Filtres de recherche ───────────────────────────────────────────────────────
class JobSearchFilters(BaseModel):
    keyword: Optional[str] = None
    location: Optional[str] = None
    contract_type: Optional[ContractType] = None
    experience_level: Optional[ExperienceLevel] = None
    work_mode: Optional[WorkMode] = None
    degree_level: Optional[DegreeLevel] = None
    skill: Optional[str] = None
    status: Optional[JobStatus] = JobStatus.ACTIVE