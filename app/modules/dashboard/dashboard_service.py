# app/modules/dashboard/dashboard_service.py

from collections import Counter
from typing import List
from sqlalchemy.orm import Session

from app.modules.jobs.job_model import Job
from app.modules.matching.recommendation_model import Recommendation
from app.modules.skill_gap.skill_gap_model import SkillGap
from app.modules.users.user_model import Profile
from app.shared.enums import MatchScoreLabel


class DashboardService:

    # ── DASHBOARD COMPLET ─────────────────────────────────────────────────────
    @staticmethod
    def get_dashboard(db: Session, user_id: int) -> dict:
        """
        Agrège toutes les statistiques pour le tableau de bord d'un utilisateur.
        """
        profile_stats = DashboardService._get_profile_stats(db, user_id)
        job_stats = DashboardService._get_job_stats(db)
        matching_stats = DashboardService._get_matching_stats(db, user_id)
        skill_gap_stats = DashboardService._get_skill_gap_stats(db, user_id)

        return {
            "user_id": user_id,
            "profile": profile_stats,
            "jobs": job_stats,
            "matching": matching_stats,
            "skill_gap": skill_gap_stats,
        }

    # ── STATS PROFIL ──────────────────────────────────────────────────────────
    @staticmethod
    def _get_profile_stats(db: Session, user_id: int) -> dict:
        profile = db.query(Profile).filter(
            Profile.user_id == user_id
        ).first()

        if not profile:
            return {
                "has_profile": False,
                "total_skills": 0,
                "top_skills": [],
                "experience_years": None,
                "education_level": None,
            }

        all_skills = profile.all_skills
        return {
            "has_profile": True,
            "total_skills": len(all_skills),
            "top_skills": all_skills[:10],
            "experience_years": getattr(profile, "experience_years", None),
            "education_level": getattr(profile, "education_level", None),
        }

    # ── STATS JOBS ────────────────────────────────────────────────────────────
    @staticmethod
    def _get_job_stats(db: Session) -> dict:
        jobs = db.query(Job).all()

        active = sum(1 for j in jobs if j.status == "active")
        expired = sum(1 for j in jobs if j.status == "expired")
        draft = sum(1 for j in jobs if j.status == "draft")

        location_counter = Counter(
            j.location for j in jobs
            if j.location and j.status == "active"
        )
        contract_counter = Counter(
            j.contract_type for j in jobs
            if j.contract_type and j.status == "active"
        )

        return {
            "total_active": active,
            "total_expired": expired,
            "total_draft": draft,
            "top_locations": [
                {"location": loc, "count": count}
                for loc, count in location_counter.most_common(5)
            ],
            "top_contract_types": [
                {"contract_type": ct, "count": count}
                for ct, count in contract_counter.most_common(5)
            ],
        }

    # ── STATS MATCHING ────────────────────────────────────────────────────────
    @staticmethod
    def _get_matching_stats(db: Session, user_id: int) -> dict:
        recs = db.query(Recommendation).filter(
            Recommendation.user_id == user_id
        ).all()

        if not recs:
            return {
                "total_recommendations": 0,
                "average_score": 0.0,
                "top_score": 0.0,
                "excellent_count": 0,
                "good_count": 0,
                "average_count": 0,
                "low_count": 0,
            }

        scores = [r.score for r in recs]
        avg_score = round(sum(scores) / len(scores), 4)
        top_score = round(max(scores), 4)

        excellent = sum(1 for r in recs if r.score_label == "Excellent")
        good = sum(1 for r in recs if r.score_label == "Good")
        average = sum(1 for r in recs if r.score_label == "Average")
        low = sum(1 for r in recs if r.score_label == "Low")

        return {
            "total_recommendations": len(recs),
            "average_score": avg_score,
            "top_score": top_score,
            "excellent_count": excellent,
            "good_count": good,
            "average_count": average,
            "low_count": low,
        }

    # ── STATS SKILL GAP ───────────────────────────────────────────────────────
    @staticmethod
    def _get_skill_gap_stats(db: Session, user_id: int) -> dict:
        gaps = db.query(SkillGap).filter(
            SkillGap.user_id == user_id
        ).all()

        if not gaps:
            return {
                "total_analyses": 0,
                "average_coverage_percent": 0,
                "top_missing_skills": [],
            }

        avg_coverage = int(
            sum(g.coverage_percent for g in gaps) / len(gaps)
        )

        all_missing: List[str] = []
        for g in gaps:
            all_missing.extend(g.missing_skills or [])

        top_missing = [
            skill for skill, _ in Counter(all_missing).most_common(10)
        ]

        return {
            "total_analyses": len(gaps),
            "average_coverage_percent": avg_coverage,
            "top_missing_skills": top_missing,
        }

    # ── TENDANCES DU MARCHÉ ───────────────────────────────────────────────────
    @staticmethod
    def get_market_trends(db: Session) -> dict:
        """
        Analyse les tendances du marché sur toutes les offres actives.
        Retourne les compétences les plus demandées.
        """
        jobs = db.query(Job).filter(Job.status == "active").all()

        all_skills: List[str] = []
        for job in jobs:
            all_skills.extend(job.required_skills or [])

        skill_counter = Counter(
            s.lower().strip() for s in all_skills if s.strip()
        )

        location_counter = Counter(
            j.location for j in jobs if j.location
        )
        contract_counter = Counter(
            j.contract_type for j in jobs if j.contract_type
        )

        return {
            "top_demanded_skills": [
                {"skill": skill, "demand_count": count}
                for skill, count in skill_counter.most_common(20)
            ],
            "total_active_jobs": len(jobs),
            "top_locations": [
                {"location": loc, "count": count}
                for loc, count in location_counter.most_common(5)
            ],
            "top_contract_types": [
                {"contract_type": ct, "count": count}
                for ct, count in contract_counter.most_common(5)
            ],
        }