# app/modules/matching/matching_service.py

from typing import List, Optional
from sqlalchemy.orm import Session

from app.modules.jobs.job_model import Job
from app.modules.matching.cosine_matcher import cosine_similarity
from app.modules.matching.recommendation_model import Recommendation
from app.modules.users.user_model import Profile
from app.shared.enums import MatchScoreLabel
from app.shared.pagination import PaginationParams, paginate_query


class MatchingService:

    @staticmethod
    def run_matching(db: Session, user_id: int) -> dict:
        profile = db.query(Profile).filter(
            Profile.user_id == user_id
        ).first()

        if not profile:
            raise ValueError(
                f"Aucun profil trouvé pour l'utilisateur {user_id}. "
                "Créez d'abord un profil."
            )

        profile_skills: List[str] = profile.all_skills

        if not profile_skills:
            raise ValueError(
                "Votre profil ne contient aucune compétence. "
                "Ajoutez des compétences manuellement ou uploadez un CV."
            )

        jobs = db.query(Job).filter(Job.status == "active").all()

        if not jobs:
            return {
                "user_id": user_id,
                "total_jobs_evaluated": 0,
                "recommendations_saved": 0,
                "top_score": 0.0,
                "message": "Aucune offre active trouvée.",
            }

        db.query(Recommendation).filter(
            Recommendation.user_id == user_id
        ).delete()

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

        db.commit()

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
    def get_recommendations(
        db: Session,
        user_id: int,
        params: PaginationParams,
        min_score: Optional[float] = None,
    ):
        query = db.query(Recommendation).filter(
            Recommendation.user_id == user_id
        )

        if min_score is not None:
            query = query.filter(Recommendation.score >= min_score)

        query = query.order_by(Recommendation.score.desc())

        return paginate_query(query, params)