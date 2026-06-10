# app/modules/skill_gap/skill_gap_service.py

from collections import Counter
from typing import List, Optional
from sqlalchemy import select, delete, desc
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.jobs.job_model import Job
from app.modules.skill_gap.skill_gap_model import SkillGap
from app.modules.users.user_model import Profile
from app.shared.pagination import PaginationParams, paginate_query


class SkillGapService:

    # ── ANALYSE SKILL GAP POUR UN JOB PRÉCIS ─────────────────────────────────
    @staticmethod
    async def analyze_for_job(db: AsyncSession, user_id: int, job_id: int) -> SkillGap:
        # 1. Récupérer le profil
        result = await db.execute(
            select(Profile).where(Profile.user_id == user_id)
        )
        profile = result.scalars().first()

        if not profile:
            raise ValueError(f"Aucun profil trouvé pour l'utilisateur {user_id}.")

        # 2. Récupérer le job
        job_result = await db.execute(
            select(Job).where(Job.id == job_id)
        )
        job = job_result.scalars().first()

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
        coverage = int(len(matching) / len(job_skills) * 100) if job_skills else 0

        # 6. Supprimer l'ancien résultat s'il existe
        await db.execute(
            delete(SkillGap).where(
                SkillGap.user_id == user_id,
                SkillGap.job_id == job_id,
            )
        )

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
        await db.commit()
        await db.refresh(skill_gap)

        return skill_gap

    # ── ANALYSE GLOBALE SUR TOUTES LES OFFRES ────────────────────────────────
    @staticmethod
    async def analyze_global(db: AsyncSession, user_id: int) -> dict:
        result = await db.execute(
            select(Profile).where(Profile.user_id == user_id)
        )
        profile = result.scalars().first()

        if not profile:
            raise ValueError(f"Aucun profil trouvé pour l'utilisateur {user_id}.")

        profile_skills = set(
            s.lower().strip() for s in profile.all_skills if s.strip()
        )

        jobs_result = await db.execute(
            select(Job).where(Job.status == "active")
        )
        jobs = jobs_result.scalars().all()

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
    async def get_by_job(db: AsyncSession, user_id: int, job_id: int) -> Optional[SkillGap]:
        result = await db.execute(
            select(SkillGap).where(
                SkillGap.user_id == user_id,
                SkillGap.job_id == job_id,
            )
        )
        return result.scalars().first()

    # ── HISTORIQUE PAGINÉ ─────────────────────────────────────────────────────
    @staticmethod
    async def get_history(
        db: AsyncSession,
        user_id: int,
        params: PaginationParams,
    ):
        query = select(SkillGap).where(
            SkillGap.user_id == user_id
        ).order_by(desc(SkillGap.coverage_percent))

        return await paginate_query(db, query, params)