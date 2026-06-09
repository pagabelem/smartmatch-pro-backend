"""
app/modules/nlp/nlp_router.py
Endpoints REST pour le module NLP.
"""

import logging
import time
from fastapi import APIRouter, Depends, status, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.responses import success_response, error_response
from app.database import get_db
from app.modules.auth.dependencies import get_current_user
from app.modules.users.user_model import User, Profile
from app.modules.nlp import nlp_service as svc
from app.modules.nlp.nlp_schema import (
    NLPProcessResponse,
    NLPBulkProcessResponse,
    NLPStatusResponse,
    NLPProfileSkillsResponse,
    NLPExtractTextRequest,
    NLPExtractTextResponse,
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/nlp", tags=["NLP"])


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

async def _check_profile_permission(
    profile_id: int,
    current_user: User,
    db: AsyncSession,
) -> None:
    """
    Vérifie que l'utilisateur a le droit d'accéder au profil.
    Propriétaire ou admin uniquement. Lève de vraies exceptions HTTP pour Pytest.
    """
    result = await db.execute(
        select(Profile).where(Profile.id == profile_id)
    )
    profile = result.scalar_one_or_none()

    if profile is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Profil {profile_id} introuvable"
        )

    is_owner = profile.user_id == current_user.id
    if not (is_owner or current_user.is_superuser):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Vous n'avez pas accès à ce profil."
        )


# ---------------------------------------------------------------------------
# POST /process/{resume_id}
# ---------------------------------------------------------------------------

@router.post(
    "/process/{resume_id}",
    response_model=None,
    status_code=status.HTTP_200_OK,
    summary="Lancer l'extraction NLP sur un CV",
)
async def process_resume(
    resume_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    from app.modules.resumes.resume_model import Resume

    result = await db.execute(select(Resume).where(Resume.id == resume_id))
    resume = result.scalar_one_or_none()

    if resume is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"CV {resume_id} introuvable"
        )

    await _check_profile_permission(resume.profile_id, current_user, db)

    result_data = await svc.process_resume(resume_id, db)

    if result_data.get("status") == "error":
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=result_data.get("message", "Erreur lors du traitement")
        )

    return success_response(
        data=NLPProcessResponse(**result_data).model_dump(),
        message="Extraction NLP terminée avec succès."
    )


# ---------------------------------------------------------------------------
# POST /process/profile/{profile_id}
# ---------------------------------------------------------------------------

@router.post(
    "/process/profile/{profile_id}",
    response_model=None,
    status_code=status.HTTP_200_OK,
    summary="Traiter tous les CVs d'un profil",
)
async def bulk_process_resumes(
    profile_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    await _check_profile_permission(profile_id, current_user, db)

    result_data = await svc.bulk_process_resumes(profile_id, db)

    return success_response(
        data=NLPBulkProcessResponse(**result_data).model_dump(),
        message=f"Traitement terminé : {result_data['processed']} CV(s) analysé(s)."
    )


# ---------------------------------------------------------------------------
# GET /status/{resume_id}
# ---------------------------------------------------------------------------

@router.get(
    "/status/{resume_id}",
    response_model=None,
    status_code=status.HTTP_200_OK,
    summary="Statut du parsing NLP",
)
async def get_nlp_status(
    resume_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    from app.modules.resumes.resume_model import Resume

    result = await db.execute(select(Resume).where(Resume.id == resume_id))
    resume = result.scalar_one_or_none()

    if resume is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"CV {resume_id} introuvable"
        )

    await _check_profile_permission(resume.profile_id, current_user, db)

    result_data = await svc.get_nlp_status(resume_id, db)

    return success_response(
        data=NLPStatusResponse(**result_data).model_dump()
    )


# ---------------------------------------------------------------------------
# GET /skills/{profile_id}
# ---------------------------------------------------------------------------

@router.get(
    "/skills/{profile_id}",
    response_model=None,
    status_code=status.HTTP_200_OK,
    summary="Compétences extraites d'un profil",
)
async def get_profile_skills(
    profile_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    await _check_profile_permission(profile_id, current_user, db)

    result_data = await svc.get_profile_skills(profile_id, db)

    return success_response(
        data=NLPProfileSkillsResponse(**result_data).model_dump()
    )


# ---------------------------------------------------------------------------
# POST /extract-text
# ---------------------------------------------------------------------------

@router.post(
    "/extract-text",
    response_model=None,
    status_code=status.HTTP_200_OK,
    summary="Extraction sur texte libre (debug)",
)
async def extract_text_debug(
    payload: NLPExtractTextRequest,
    current_user: User = Depends(get_current_user),
):
    # Sécurisation du rôle Admin (Le 401 est géré en amont par get_current_user)
    if not current_user.is_superuser:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Endpoint réservé aux administrateurs."
        )

    start = time.perf_counter()

    skills = svc.extract_text_debug(payload.text)

    elapsed_ms = int((time.perf_counter() - start) * 1000)

    return success_response(
        data=NLPExtractTextResponse(
            skills=skills,
            processing_time_ms=elapsed_ms,
            total=len(skills),
        ).model_dump(),
        message="Extraction terminée."
    )