# app/modules/skill_gap/skill_gap_service.py

from collections import Counter
from typing import List, Optional
from sqlalchemy.orm import Session

from app.modules.jobs.job_model import Job
from app.modules.skill_gap.skill_gap_model import SkillGap
from app.modules.users.user_model import Profile
from app.shared.pagination import PaginationParams, paginate_query


class SkillGapService:

    # ── ANALYSE SKILL GAP POUR UN JOB PRÉCIS ─────────────────────────────────
    @staticmethod
    def analyze_for_job(db: Session, user_id: int, job_id: int) -> SkillGap:
        """
        Compare les compétences du profil avec celles requises par une offre.
        Sauvegarde et retourne le résultat.
        """
        # 1. Récupérer le profil
        profile = db.query(Profile).filter(
            Profile.user_id == user_id
        ).first()

        if not profile:
            raise ValueError(
                f"Aucun profil trouvé pour l'utilisateur {user_id}."
            )

        # 2. Récupérer le job
        job = db.query(Job).filter(Job.id == job_id).first()

        if not job:
            raise ValueError(f"Offre d'emploi {job_id} introuvable.")

        # 3. Normaliser les compétences
        profile_skills = set(
            s.lower().strip() for s in profile.all_skills if s.strip()
        )
        job_skills = set(
            s.lower().strip() for s in (job.required_skills or []) if s.strip()
        )

        # 4. Calculer les trois ensembles
        matching = sorted(profile_skills & job_skills)
        missing = sorted(job_skills - profile_skills)
        extra = sorted(profile_skills - job_skills)

        # 5. Calculer le pourcentage de couverture
        if job_skills:
            coverage = int(len(matching) / len(job_skills) * 100)
        else:
            coverage = 0

        # 6. Supprimer l'ancien résultat s'il existe
        db.query(SkillGap).filter(
            SkillGap.user_id == user_id,
            SkillGap.job_id == job_id,
        ).delete()

        # 7. Sauvegarder le nouveau résultat
        skill_gap = SkillGap(
            user_id=user_id,
            job_id=job_id,
            matching_skills=matching,
            missing_skills=missing,
            extra_skills=extra,
            coverage_percent=coverage,
        )
        db.add(skill_gap)
        db.commit()
        db.refresh(skill_gap)

        return skill_gap

    # ── ANALYSE GLOBALE SUR TOUTES LES OFFRES ────────────────────────────────
    @staticmethod
    def analyze_global(db: Session, user_id: int) -> dict:
        """
        Analyse le skill gap sur toutes les offres actives.
        Retourne un résumé avec les compétences les plus manquantes.
        """
        profile = db.query(Profile).filter(
            Profile.user_id == user_id
        ).first()

        if not profile:
            raise ValueError(
                f"Aucun profil trouvé pour l'utilisateur {user_id}."
            )

        profile_skills = set(
            s.lower().strip() for s in profile.all_skills if s.strip()
        )

        jobs = db.query(Job).filter(Job.status == "active").all()

        if not jobs:
            return {
                "user_id": user_id,
                "total_jobs_analyzed": 0,
                "average_coverage_percent": 0,
                "top_missing_skills": [],
                "message": "Aucune offre active trouvée.",
            }

        all_missing: List[str] = []
        total_coverage = 0

        for job in jobs:
            job_skills = set(
                s.lower().strip()
                for s in (job.required_skills or [])
                if s.strip()
            )
            if not job_skills:
                continue

            matching = profile_skills & job_skills
            missing = job_skills - profile_skills
            coverage = int(len(matching) / len(job_skills) * 100)

            total_coverage += coverage
            all_missing.extend(list(missing))

        avg_coverage = int(total_coverage / len(jobs)) if jobs else 0

        # Top 10 compétences les plus manquantes
        top_missing = [
            skill for skill, _ in Counter(all_missing).most_common(10)
        ]

        return {
            "user_id": user_id,
            "total_jobs_analyzed": len(jobs),
            "average_coverage_percent": avg_coverage,
            "top_missing_skills": top_missing,
            "message": (
                f"Analyse terminée sur {len(jobs)} offre(s). "
                f"Couverture moyenne : {avg_coverage}%."
            ),
        }

    # ── GET SKILL GAP PAR JOB ─────────────────────────────────────────────────
    @staticmethod
    def get_by_job(db: Session, user_id: int, job_id: int) -> Optional[SkillGap]:
        """Récupère le skill gap déjà calculé pour un user/job."""
        return db.query(SkillGap).filter(
            SkillGap.user_id == user_id,
            SkillGap.job_id == job_id,
        ).first()

    # ── HISTORIQUE PAGINÉ ─────────────────────────────────────────────────────
    @staticmethod
    def get_history(
        db: Session,
        user_id: int,
        params: PaginationParams,
    ):
        """Liste paginée des skill gaps d'un utilisateur."""
        query = db.query(SkillGap).filter(
            SkillGap.user_id == user_id
        ).order_by(SkillGap.coverage_percent.desc())

        return paginate_query(query, params)