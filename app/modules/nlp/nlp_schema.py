from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class NLPProcessRequest(BaseModel):
    resume_id: int = Field(..., description="ID du CV à traiter")


class NLPProcessResponse(BaseModel):
    resume_id: int
    skills_extracted: list[str] = Field(
        default_factory=list,
        description="Compétences extraites du CV",
    )
    processing_time_ms: int = Field(..., description="Temps de traitement en millisecondes")
    status: str = Field(..., description="'success' | 'already_parsed' | 'error'")
    message: Optional[str] = None


class NLPBulkProcessResponse(BaseModel):
    profile_id: int
    processed: int = Field(..., description="Nombre de CVs traités")
    skipped: int = Field(..., description="Nombre de CVs déjà parsés (ignorés)")
    total_skills: int = Field(..., description="Nombre total de compétences extraites")
    processing_time_ms: int
    status: str


class NLPStatusResponse(BaseModel):
    resume_id: int
    is_parsed: bool
    processed_at: Optional[datetime] = Field(
        None,
        description="Date de dernière mise à jour (updated_at du CV)",
    )
    raw_text_length: Optional[int] = Field(
        None,
        description="Longueur du texte brut disponible",
    )


class NLPProfileSkillsResponse(BaseModel):
    profile_id: int
    skills: list[str] = Field(default_factory=list)
    total: int = Field(..., description="Nombre total de compétences")


class NLPExtractTextRequest(BaseModel):
    text: str = Field(..., min_length=1, description="Texte libre à analyser")


class NLPExtractTextResponse(BaseModel):
    skills: list[str] = Field(default_factory=list)
    processing_time_ms: int
    total: int = Field(..., description="Nombre de compétences trouvées")