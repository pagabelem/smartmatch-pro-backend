"""
app/modules/resumes/resume_router.py
Endpoints REST pour le module Resumes.

Routes :
  POST   /api/v1/resumes/upload              — Upload CV (multipart/form-data)
  GET    /api/v1/resumes/{resume_id}         — Récupérer un CV par ID
  GET    /api/v1/resumes/{resume_id}/text    — Texte brut extrait
  GET    /api/v1/resumes/profile/{profile_id} — CVs d'un profil (paginé)
  DELETE /api/v1/resumes/{resume_id}         — Supprimer un CV
"""

import logging
from pathlib import Path

from fastapi import APIRouter, Depends, UploadFile, File, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from sqlalchemy import select

from app.config import settings
from app.core.exceptions import ForbiddenException, NotFoundException
from app.core.responses import success_response, error_response
from app.database import get_db
from app.modules.auth.dependencies import get_current_user
from app.modules.users.user_model import User
from app.modules.resumes import resume_service as svc
from app.modules.resumes.resume_schema import (
    ResumeUploadResponse,
    ResumeResponse,
    ResumeListResponse,
    ResumeTextResponse,
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/resumes", tags=["Resumes"])


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

async def _assert_owner_or_admin(
    resume_profile_id: int, 
    current_user: User, 
    db: AsyncSession
) -> None:
    """Vérifie que l'utilisateur est propriétaire du profil ou admin."""
    # Charger explicitement le profile
    result = await db.execute(
        select(User).where(User.id == current_user.id).options(selectinload(User.profile))
    )
    user_with_profile = result.scalar_one()
    
    is_owner = (
        user_with_profile.profile is not None
        and user_with_profile.profile.id == resume_profile_id
    )
    if not (is_owner or current_user.is_superuser):
        raise ForbiddenException("Accès refusé à ce CV.")


# ---------------------------------------------------------------------------
# POST /upload
# ---------------------------------------------------------------------------

@router.post(
    "/upload",
    response_model=None,
    status_code=status.HTTP_201_CREATED,
    summary="Upload d'un CV (PDF ou DOCX)",
    description=(
        "Téléverse un fichier CV au format PDF ou DOCX. "
        "Valide l'extension et la taille avant écriture. "
        "Extrait le texte brut et le stocke pour le module NLP."
    ),
)
async def upload_resume(
    file: UploadFile = File(..., description="Fichier CV (PDF ou DOCX)"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Upload un CV et extrait son texte brut."""
    # Charger explicitement le profile
    result = await db.execute(
        select(User).where(User.id == current_user.id).options(selectinload(User.profile))
    )
    current_user = result.scalar_one()
    
    if current_user.profile is None:
        return error_response("Vous devez d'abord créer un profil.", code=400)

    profile_id = current_user.profile.id

    # 1. Sauvegarde physique + validation
    file_path, file_size, mime_type = await svc.save_resume_file(file, profile_id)

    # 2. Extraction texte brut
    absolute_path = str(Path(settings.UPLOAD_DIR) / file_path)
    raw_text = svc.extract_raw_text(absolute_path, mime_type)

    # 3. Enregistrement BDD
    resume = await svc.create_resume_record(
        db=db,
        profile_id=profile_id,
        filename=file.filename or "resume",
        file_path=file_path,
        file_size=file_size,
        mime_type=mime_type,
        raw_text=raw_text,
    )

    response_data = ResumeUploadResponse.model_validate(resume).model_dump()
    return success_response(data=response_data, message="CV uploadé avec succès.")


# ---------------------------------------------------------------------------
# GET /profile/{profile_id}
# ---------------------------------------------------------------------------

@router.get(
    "/profile/{profile_id}",
    response_model=None,
    summary="Liste des CVs d'un profil",
    description="Retourne tous les CVs associés à un profil, paginés.",
)
async def list_resumes_by_profile(
    profile_id: int,
    page: int = Query(1, ge=1, description="Numéro de page"),
    limit: int = Query(10, ge=1, le=50, description="CVs par page"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Liste paginée des CVs d'un profil."""
    await _assert_owner_or_admin(profile_id, current_user, db)

    items, total = await svc.get_resumes_by_profile(db, profile_id, page, limit)
    pages = svc.compute_pages(total, limit)

    response_data = ResumeListResponse(
        items=[ResumeResponse.model_validate(r) for r in items],
        total=total,
        page=page,
        limit=limit,
        pages=pages,
    ).model_dump()

    return success_response(data=response_data)


# ---------------------------------------------------------------------------
# GET /{resume_id}
# ---------------------------------------------------------------------------

@router.get(
    "/{resume_id}",
    response_model=None,
    summary="Récupérer un CV par ID",
)
async def get_resume(
    resume_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Retourne les métadonnées complètes d'un CV, incluant le texte extrait."""
    resume = await svc.get_resume_by_id(db, resume_id)
    await _assert_owner_or_admin(resume.profile_id, current_user, db)

    return success_response(
        data=ResumeResponse.model_validate(resume).model_dump()
    )


# ---------------------------------------------------------------------------
# GET /{resume_id}/text
# ---------------------------------------------------------------------------

@router.get(
    "/{resume_id}/text",
    response_model=None,
    summary="Texte brut extrait d'un CV",
    description="Retourne uniquement le texte brut issu du parsing du CV.",
)
async def get_resume_text(
    resume_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Retourne le champ `raw_text` du CV."""
    resume = await svc.get_resume_by_id(db, resume_id)
    await _assert_owner_or_admin(resume.profile_id, current_user, db)

    # ✅ CORRECTION : utiliser un dictionnaire simple au lieu de ResumeTextResponse
    return success_response(
        data={
            "id": resume.id,
            "raw_text": resume.raw_text
        }
    )


# ---------------------------------------------------------------------------
# DELETE /{resume_id}
# ---------------------------------------------------------------------------

@router.delete(
    "/{resume_id}",
    status_code=status.HTTP_200_OK,
    summary="Supprimer un CV",
    description="Supprime le fichier physique ET l'enregistrement en base.",
)
async def delete_resume(
    resume_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Suppression complète d'un CV (fichier + BDD)."""
    resume = await svc.get_resume_by_id(db, resume_id)
    await _assert_owner_or_admin(resume.profile_id, current_user, db)

    await svc.delete_resume(db, resume_id)
    return success_response(message=f"CV '{resume.filename}' supprimé avec succès.")