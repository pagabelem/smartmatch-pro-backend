# app/modules/dashboard/dashboard_router.py

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.responses import ok
from app.dependencies import get_db, get_current_active_user
from app.modules.dashboard.dashboard_schema import (
    DashboardStats,
    MarketTrendsResponse,
)
from app.modules.dashboard.dashboard_service import DashboardService
from app.modules.users.user_model import User

router = APIRouter(prefix="/dashboard", tags=["Dashboard"])


@router.get(
    "/{user_id}",
    status_code=status.HTTP_200_OK,
    summary="Tableau de bord complet d'un utilisateur",
)
def get_dashboard(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """
    Retourne toutes les statistiques agrégées :
    profil, offres, matching, skill gap.
    """
    if current_user.id != user_id and not current_user.is_superuser:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Accès non autorisé.",
        )

    result = DashboardService.get_dashboard(db, user_id)

    return ok(
        data=DashboardStats(**result).model_dump(mode="json"),
        message="Tableau de bord récupéré avec succès.",
    )


@router.get(
    "/market/trends",
    status_code=status.HTTP_200_OK,
    summary="Tendances globales du marché de l'emploi",
)
def get_market_trends(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """
    Retourne les compétences les plus demandées,
    les localisations et types de contrats les plus fréquents.
    """
    result = DashboardService.get_market_trends(db)

    return ok(
        data=MarketTrendsResponse(**result).model_dump(mode="json"),
        message="Tendances du marché récupérées avec succès.",
    )