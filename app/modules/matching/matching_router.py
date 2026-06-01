# app/modules/matching/matching_router.py

from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.core.responses import ok, created
from app.dependencies import get_db, get_current_active_user
from app.modules.matching.matching_schema import (
    MatchingRunResponse,
    RecommendationListResponse,
    RecommendationResponse,
)
from app.modules.matching.matching_service import MatchingService
from app.modules.users.user_model import User
from app.shared.pagination import PaginationParams

router = APIRouter(prefix="/matching", tags=["Matching"])


@router.post(
    "/run/{user_id}",
    status_code=status.HTTP_200_OK,
    summary="Lancer le calcul de matching pour un utilisateur",
)
def run_matching(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """
    Calcule le score cosinus entre les compétences du profil
    et toutes les offres actives. Sauvegarde les résultats.
    """
    if current_user.id != user_id and not current_user.is_superuser:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Vous ne pouvez lancer le matching que pour votre propre profil.",
        )

    try:
        result = MatchingService.run_matching(db, user_id)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )

    return ok(
        data=MatchingRunResponse(**result).model_dump(mode="json"),
        message=result["message"],
    )


@router.get(
    "/recommendations/{user_id}",
    status_code=status.HTTP_200_OK,
    summary="Récupérer les recommandations d'un utilisateur",
)
def get_recommendations(
    user_id: int,
    min_score: Optional[float] = Query(
        None,
        ge=0.0,
        le=1.0,
        description="Score minimum (ex: 0.5 pour ≥ 50%)",
    ),
    params: PaginationParams = Depends(),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """
    Liste paginée des recommandations triées par score décroissant.
    """
    if current_user.id != user_id and not current_user.is_superuser:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Vous ne pouvez voir que vos propres recommandations.",
        )

    page = MatchingService.get_recommendations(
        db, user_id, params, min_score=min_score
    )

    return ok(
        data=RecommendationListResponse(
            items=[
                RecommendationResponse.model_validate(r).model_dump(mode="json")
                for r in page.items
            ],
            **page.to_dict(),
        ).model_dump(mode="json"),
    )