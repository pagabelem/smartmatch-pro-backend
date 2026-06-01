# app/modules/skill_gap/skill_gap_router.py

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.responses import ok
from app.dependencies import get_db, get_current_active_user
from app.modules.skill_gap.skill_gap_schema import (
    SkillGapListResponse,
    SkillGapResponse,
    SkillGapSummary,
)
from app.modules.skill_gap.skill_gap_service import SkillGapService
from app.modules.users.user_model import User
from app.shared.pagination import PaginationParams

router = APIRouter(prefix="/skill-gap", tags=["Skill Gap"])


@router.post(
    "/{user_id}/{job_id}",
    status_code=status.HTTP_200_OK,
    summary="Analyser le skill gap pour une offre précise",
)
def analyze_for_job(
    user_id: int,
    job_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """
    Compare les compétences du profil avec celles requises par l'offre.
    Retourne les skills manquantes, en commun, et en surplus.
    """
    if current_user.id != user_id and not current_user.is_superuser:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Accès non autorisé.",
        )

    try:
        result = SkillGapService.analyze_for_job(db, user_id, job_id)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )

    return ok(
        data=SkillGapResponse.model_validate(result).model_dump(mode="json"),
        message=f"Analyse skill gap terminée. Couverture : {result.coverage_percent}%.",
    )


@router.get(
    "/{user_id}/global",
    status_code=status.HTTP_200_OK,
    summary="Résumé global du skill gap sur toutes les offres actives",
)
def analyze_global(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """
    Analyse le skill gap sur toutes les offres actives.
    Retourne la couverture moyenne et les top 10 compétences manquantes.
    """
    if current_user.id != user_id and not current_user.is_superuser:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Accès non autorisé.",
        )

    try:
        result = SkillGapService.analyze_global(db, user_id)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )

    return ok(
        data=SkillGapSummary(**result).model_dump(mode="json"),
        message=result["message"],
    )


@router.get(
    "/{user_id}/{job_id}",
    status_code=status.HTTP_200_OK,
    summary="Récupérer le skill gap déjà calculé pour une offre",
)
def get_skill_gap(
    user_id: int,
    job_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Retourne le dernier skill gap calculé pour ce user/job."""
    if current_user.id != user_id and not current_user.is_superuser:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Accès non autorisé.",
        )

    result = SkillGapService.get_by_job(db, user_id, job_id)

    if not result:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Aucune analyse trouvée. Lancez d'abord POST /{user_id}/{job_id}.",
        )

    return ok(
        data=SkillGapResponse.model_validate(result).model_dump(mode="json"),
    )


@router.get(
    "/{user_id}/history",
    status_code=status.HTTP_200_OK,
    summary="Historique paginé des analyses skill gap",
)
def get_history(
    user_id: int,
    params: PaginationParams = Depends(),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Liste paginée de tous les skill gaps calculés pour un utilisateur."""
    if current_user.id != user_id and not current_user.is_superuser:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Accès non autorisé.",
        )

    page = SkillGapService.get_history(db, user_id, params)

    return ok(
        data=SkillGapListResponse(
            items=[
                SkillGapResponse.model_validate(r).model_dump(mode="json")
                for r in page.items
            ],
            **page.to_dict(),
        ).model_dump(mode="json"),
    )