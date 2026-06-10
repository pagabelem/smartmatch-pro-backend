# app/modules/favorites/favorite_service.py

from sqlalchemy import select, func, delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ConflictException, NotFoundException
from app.modules.favorites.favorite_model import Favorite
from app.modules.jobs.job_service import JobService
from app.shared.pagination import PaginationParams, paginate_query


class FavoriteService:
    """Service CRUD async pour les favoris utilisateur."""

    # ── ADD FAVORITE ───────────────────────────────────────────────────────────
    @staticmethod
    async def add(db: AsyncSession, user_id: int, job_id: int) -> Favorite:
        # Vérifier que l'offre existe
        await JobService.get_by_id(db, job_id)

        # Vérifier qu'elle n'est pas déjà en favori
        result = await db.execute(
            select(Favorite).where(
                Favorite.user_id == user_id,
                Favorite.job_id == job_id,
            )
        )
        existing = result.scalars().first()
        if existing:
            raise ConflictException(
                f"L'offre {job_id} est déjà dans vos favoris."
            )

        favorite = Favorite(user_id=user_id, job_id=job_id)
        db.add(favorite)
        await db.commit()
        await db.refresh(favorite)
        return favorite

    # ── REMOVE FAVORITE ────────────────────────────────────────────────────────
    @staticmethod
    async def remove(db: AsyncSession, user_id: int, job_id: int) -> dict:
        result = await db.execute(
            select(Favorite).where(
                Favorite.user_id == user_id,
                Favorite.job_id == job_id,
            )
        )
        favorite = result.scalars().first()
        if not favorite:
            raise NotFoundException(
                f"L'offre {job_id} n'est pas dans vos favoris."
            )
        await db.delete(favorite)
        await db.commit()
        return {"message": f"Offre {job_id} retirée de vos favoris."}

    # ── GET USER FAVORITES ─────────────────────────────────────────────────────
    @staticmethod
    async def get_user_favorites(
        db: AsyncSession,
        user_id: int,
        params: PaginationParams,
    ):
        query = select(Favorite).where(
            Favorite.user_id == user_id
        ).order_by(Favorite.created_at.desc())
        return await paginate_query(db, query, params)

    # ── CHECK IS FAVORITE ──────────────────────────────────────────────────────
    @staticmethod
    async def is_favorite(db: AsyncSession, user_id: int, job_id: int) -> bool:
        result = await db.execute(
            select(Favorite).where(
                Favorite.user_id == user_id,
                Favorite.job_id == job_id,
            )
        )
        return result.scalars().first() is not None

    # ── COUNT USER FAVORITES ───────────────────────────────────────────────────
    @staticmethod
    async def count_user_favorites(db: AsyncSession, user_id: int) -> int:
        result = await db.execute(
            select(func.count()).where(Favorite.user_id == user_id).select_from(Favorite)
        )
        return result.scalar()