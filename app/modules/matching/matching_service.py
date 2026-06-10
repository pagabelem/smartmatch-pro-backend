# app/modules/matching/matching_service.py

from typing import List, Optional
from sqlalchemy import select, delete, desc
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.modules.jobs.job_model import Job
from app.modules.matching.cosine_matcher import cosine_similarity
from app.modules.matching.recommendation_model import Recommendation
from app.modules.users.user_model import Profile
from app.shared.enums import MatchScoreLabel
from app.shared.pagination import PaginationParams, paginate_query


class MatchingService:

    @staticmethod
    async def run_matching(db: AsyncSession, user_id: int) -> dict:
        # 1. Récupérer le profil
        result = await db.execute(
            select(Profile).where(Profile.user_id == user_id)
        )
        profile = result.scalars().first()

        if not profile:
            raise ValueError(
                f"Aucun profil trouvé pour l'utilisateur {user_id}. "
                "Créez d'abord un profil."
            )

        # 2. Récupérer les compétences via la propriété all_skills du Membre 1
        profile_skills: List[str] = profile.all_skills

        if not profile_skills:
            raise ValueError(
                "Votre profil ne contient aucune compétence. "
                "Ajoutez des compétences manuellement ou uploadez un CV."
            )

        # 3. Récupérer toutes les offres actives
        jobs_result = await db.execute(
            select(Job).where(Job.status == "active")
        )
        jobs = jobs_result.scalars().all()

        if not jobs:
            return {
                "user_id": user_id,
                "total_jobs_evaluated": 0,
                "recommendations_saved": 0,
                "top_score": 0.0,
                "message": "Aucune offre active trouvée.",
            }

        # 4. Supprimer les anciennes recommandations
        await db.execute(
            delete(Recommendation).where(Recommendation.user_id == user_id)
        )

        # 5. Calculer les scores et sauvegarder
        saved = 0
        top_score = 0.0

        for job in jobs:
            job_skills: List[str] = job.required_skills or []

            if not job_skills:
                continue

            score = cosine_similarity(profile_skills, job_skills)

            if score > 0.0:
                label = MatchScoreLabel.from_score(score * 100).value
                rec = Recommendation(
                    user_id=user_id,
                    job_id=job.id,
                    score=score,
                    score_label=label,
                )
                db.add(rec)
                saved += 1
                if score > top_score:
                    top_score = score

        await db.commit()

        return {
            "user_id": user_id,
            "total_jobs_evaluated": len(jobs),
            "recommendations_saved": saved,
            "top_score": round(top_score, 4),
            "message": (
                f"{saved} recommandation(s) générée(s) "
                f"sur {len(jobs)} offre(s) évaluée(s)."
            ),
        }

    @staticmethod
    async def get_recommendations(
        db: AsyncSession,
        user_id: int,
        params: PaginationParams,
        min_score: Optional[float] = None,
    ):
        query = select(Recommendation).where(
            Recommendation.user_id == user_id
        )

        if min_score is not None:
            query = query.where(Recommendation.score >= min_score)

        query = query.order_by(desc(Recommendation.score))

        return await paginate_query(db, query, params)