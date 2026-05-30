# app/modules/favorites/favorite_router.py

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.core.responses import created, ok
from app.dependencies import get_db
from app.modules.favorites.favorite_schema import FavoriteCreate, FavoriteResponse
from app.modules.favorites.favorite_service import FavoriteService
from app.modules.jobs.job_schema import JobResponse
from app.modules.jobs.job_model import Job
from app.shared.pagination import PaginationParams

router = APIRouter(
    prefix="/favorites",
    tags=["Favorites — Offres en favoris"],
)


# ── POST /api/v1/favorites/ ────────────────────────────────────────────────────
@router.post(
    "/",
    status_code=status.HTTP_201_CREATED,
    summary="Ajouter une offre en favori",
)
def add_favorite(
    data: FavoriteCreate,
    user_id: int = Query(..., description="ID de l'utilisateur"),
    db: Session = Depends(get_db),
):
    """
    Ajoute une offre dans les favoris d'un utilisateur.
    HTTP 409 si déjà en favori. HTTP 404 si l'offre n'existe pas.
    """
    favorite = FavoriteService.add(db, user_id, data.job_id)
    return created(
        data=FavoriteResponse.model_validate(favorite).model_dump(mode="json"),
        message=f"Offre {data.job_id} ajoutée aux favoris.",
    )


# ── DELETE /api/v1/favorites/ ─────────────────────────────────────────────────
@router.delete(
    "/",
    status_code=status.HTTP_200_OK,
    summary="Retirer une offre des favoris",
)
def remove_favorite(
    job_id: int = Query(..., description="ID de l'offre à retirer"),
    user_id: int = Query(..., description="ID de l'utilisateur"),
    db: Session = Depends(get_db),
):
    """Retire une offre des favoris. HTTP 404 si le favori n'existe pas."""
    result = FavoriteService.remove(db, user_id, job_id)
    return ok(message=result["message"])


# ── GET /api/v1/favorites/ ────────────────────────────────────────────────────
@router.get(
    "/",
    status_code=status.HTTP_200_OK,
    summary="Lister les favoris d'un utilisateur",
)
def get_favorites(
    user_id: int = Query(..., description="ID de l'utilisateur"),
    params: PaginationParams = Depends(),
    db: Session = Depends(get_db),
):
    """Liste paginée des offres en favoris pour un utilisateur donné."""
    page = FavoriteService.get_user_favorites(db, user_id, params)

    # Enrichir avec les détails de l'offre
    result = []
    for fav in page.items:
        job = db.query(Job).filter(Job.id == fav.job_id).first()
        result.append({
            "id": fav.id,
            "user_id": fav.user_id,
            "created_at": fav.created_at.isoformat(),
            "job": JobResponse.model_validate(job).model_dump(mode="json") if job else None,
        })

    return ok(data=result, meta=page.to_dict())


# ── GET /api/v1/favorites/check ───────────────────────────────────────────────
@router.get(
    "/check",
    status_code=status.HTTP_200_OK,
    summary="Vérifier si une offre est en favori",
)
def check_favorite(
    job_id: int = Query(..., description="ID de l'offre"),
    user_id: int = Query(..., description="ID de l'utilisateur"),
    db: Session = Depends(get_db),
):
    """Retourne true/false selon si l'offre est dans les favoris."""
    is_fav = FavoriteService.is_favorite(db, user_id, job_id)
    return ok(
        data={"is_favorite": is_fav, "job_id": job_id, "user_id": user_id}
    )


# ── GET /api/v1/favorites/count ───────────────────────────────────────────────
@router.get(
    "/count",
    status_code=status.HTTP_200_OK,
    summary="Nombre de favoris d'un utilisateur",
)
def count_favorites(
    user_id: int = Query(..., description="ID de l'utilisateur"),
    db: Session = Depends(get_db),
):
    """Retourne le nombre total de favoris pour un utilisateur."""
    count = FavoriteService.count_user_favorites(db, user_id)
    return ok(data={"user_id": user_id, "total_favorites": count})