# app/modules/favorites/favorite_service.py

from sqlalchemy.orm import Session

from app.core.exceptions import ConflictException, NotFoundException
from app.modules.favorites.favorite_model import Favorite
from app.modules.jobs.job_service import JobService
from app.shared.pagination import PaginationParams, paginate_query


class FavoriteService:
    """Service CRUD pour les favoris utilisateur."""

    # ── ADD FAVORITE ───────────────────────────────────────────────────────────
    @staticmethod
    def add(db: Session, user_id: int, job_id: int) -> Favorite:
        """
        Ajoute une offre en favori pour un utilisateur.
        Lève ConflictException si déjà en favori.
        Lève NotFoundException si l'offre n'existe pas.
        """
        # Vérifier que l'offre existe
        JobService.get_by_id(db, job_id)

        # Vérifier qu'elle n'est pas déjà en favori
        existing = db.query(Favorite).filter(
            Favorite.user_id == user_id,
            Favorite.job_id == job_id,
        ).first()
        if existing:
            raise ConflictException(
                f"L'offre {job_id} est déjà dans vos favoris."
            )

        favorite = Favorite(user_id=user_id, job_id=job_id)
        db.add(favorite)
        db.commit()
        db.refresh(favorite)
        return favorite

    # ── REMOVE FAVORITE ────────────────────────────────────────────────────────
    @staticmethod
    def remove(db: Session, user_id: int, job_id: int) -> dict:
        """
        Retire une offre des favoris.
        Lève NotFoundException si le favori n'existe pas.
        """
        favorite = db.query(Favorite).filter(
            Favorite.user_id == user_id,
            Favorite.job_id == job_id,
        ).first()
        if not favorite:
            raise NotFoundException(
                f"L'offre {job_id} n'est pas dans vos favoris."
            )
        db.delete(favorite)
        db.commit()
        return {"message": f"Offre {job_id} retirée de vos favoris."}

    # ── GET USER FAVORITES ─────────────────────────────────────────────────────
    @staticmethod
    def get_user_favorites(
        db: Session,
        user_id: int,
        params: PaginationParams,
    ):
        """Liste paginée des favoris d'un utilisateur."""
        query = db.query(Favorite).filter(
            Favorite.user_id == user_id
        ).order_by(Favorite.created_at.desc())
        return paginate_query(query, params)

    # ── CHECK IS FAVORITE ──────────────────────────────────────────────────────
    @staticmethod
    def is_favorite(db: Session, user_id: int, job_id: int) -> bool:
        """Vérifie si une offre est dans les favoris d'un utilisateur."""
        return db.query(Favorite).filter(
            Favorite.user_id == user_id,
            Favorite.job_id == job_id,
        ).first() is not None

    # ── COUNT USER FAVORITES ───────────────────────────────────────────────────
    @staticmethod
    def count_user_favorites(db: Session, user_id: int) -> int:
        """Nombre total de favoris d'un utilisateur."""
        return db.query(Favorite).filter(
            Favorite.user_id == user_id
        ).count()