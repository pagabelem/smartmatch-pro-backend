# app/modules/jobs/job_router.py

from typing import Optional

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.core.responses import created, ok
from app.dependencies import get_db
from app.modules.jobs.job_schema import JobCreate, JobResponse, JobUpdate
from app.modules.jobs.job_service import JobService
from app.shared.enums import (
    ContractType,
    ExperienceLevel,
    JobStatus,
    WorkMode,
)
from app.shared.pagination import PaginationParams

router = APIRouter(
    prefix="/jobs",
    tags=["Jobs — Offres d'emploi"],
)


# ── POST /api/v1/jobs/ ─────────────────────────────────────────────────────────
@router.post(
    "/",
    status_code=status.HTTP_201_CREATED,
    summary="Créer une offre d'emploi",
)
def create_job(
    data: JobCreate,
    db: Session = Depends(get_db),
):
    """Ajoute une offre d'emploi manuellement."""
    job = JobService.create(db, data)
    return created(
        data=JobResponse.model_validate(job).model_dump(mode="json"),
        message=f"Offre '{job.title}' créée avec succès.",
    )


# ── GET /api/v1/jobs/ ──────────────────────────────────────────────────────────
@router.get(
    "/",
    status_code=status.HTTP_200_OK,
    summary="Lister les offres (paginé + filtres)",
)
def list_jobs(
    keyword: Optional[str] = Query(None, description="Recherche dans titre, entreprise, description"),
    location: Optional[str] = Query(None, description="Filtrer par ville"),
    contract_type: Optional[ContractType] = Query(None, description="CDI, CDD, Stage…"),
    experience_level: Optional[ExperienceLevel] = Query(None, description="junior, mid, senior…"),
    work_mode: Optional[WorkMode] = Query(None, description="on_site, remote, hybrid"),
    skill: Optional[str] = Query(None, description="Filtrer par compétence requise"),
    job_status: Optional[JobStatus] = Query(JobStatus.ACTIVE, alias="status",
                                            description="active, expired, draft…"),
    params: PaginationParams = Depends(),
    db: Session = Depends(get_db),
):
    """Liste paginée des offres avec filtres combinables."""
    page = JobService.get_all(
        db=db,
        params=params,
        keyword=keyword,
        location=location,
        contract_type=contract_type.value if contract_type else None,
        experience_level=experience_level.value if experience_level else None,
        work_mode=work_mode.value if work_mode else None,
        skill=skill,
        status=job_status.value if job_status else None,
    )
    return ok(
        data=[JobResponse.model_validate(j).model_dump(mode="json") for j in page.items],
        meta=page.to_dict(),
    )


# ── GET /api/v1/jobs/{job_id} ──────────────────────────────────────────────────
@router.get(
    "/{job_id}",
    status_code=status.HTTP_200_OK,
    summary="Récupérer une offre par son ID",
)
def get_job(
    job_id: int,
    db: Session = Depends(get_db),
):
    """Retourne le détail complet d'une offre. HTTP 404 si introuvable."""
    job = JobService.get_by_id(db, job_id)
    return ok(data=JobResponse.model_validate(job).model_dump(mode="json"))


# ── PUT /api/v1/jobs/{job_id} ──────────────────────────────────────────────────
@router.put(
    "/{job_id}",
    status_code=status.HTTP_200_OK,
    summary="Mettre à jour une offre",
)
def update_job(
    job_id: int,
    data: JobUpdate,
    db: Session = Depends(get_db),
):
    """Mise à jour partielle. Seuls les champs envoyés sont modifiés."""
    job = JobService.update(db, job_id, data)
    return ok(
        data=JobResponse.model_validate(job).model_dump(mode="json"),
        message=f"Offre '{job.title}' mise à jour.",
    )


# ── DELETE /api/v1/jobs/{job_id} ───────────────────────────────────────────────
@router.delete(
    "/{job_id}",
    status_code=status.HTTP_200_OK,
    summary="Supprimer une offre",
)
def delete_job(
    job_id: int,
    db: Session = Depends(get_db),
):
    """Suppression définitive. HTTP 404 si introuvable."""
    result = JobService.delete(db, job_id)
    return ok(message=result["message"])