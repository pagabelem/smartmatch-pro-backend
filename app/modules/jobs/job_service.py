# app/modules/jobs/job_service.py

from typing import Optional
from sqlalchemy import or_, select, desc, delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import NotFoundException
from app.modules.jobs.job_model import Job
from app.modules.jobs.job_schema import JobCreate, JobUpdate
from app.shared.enums import JobStatus
from app.shared.pagination import PaginationParams, paginate_query
from app.shared.utils import normalize_skill


class JobService:
    """Service CRUD complet et asynchrone pour les offres d'emploi."""

    # ── CREATE (ASYNC) ────────────────────────────────────────────────────────
    @staticmethod
    async def create(db: AsyncSession, data: JobCreate) -> Job:
        """Crée une nouvelle offre d'emploi de manière asynchrone."""
        job = Job(
            title=data.title,
            company=data.company,
            description=data.description,
            location=data.location,
            url=data.url,
            contract_type=data.contract_type.value,
            experience_level=data.experience_level.value,
            work_mode=data.work_mode.value,
            degree_level=data.degree_level.value if data.degree_level else None,
            required_skills=data.required_skills,
            salary_min=data.salary_min,
            salary_max=data.salary_max,
            salary_currency=data.salary_currency,
            status=data.status.value,
            source=data.source.value,
            published_at=data.published_at,
            expires_at=data.expires_at,
        )
        db.add(job)
        await db.commit()
        await db.refresh(job)
        return job

    # ── READ BY ID (ASYNC) ────────────────────────────────────────────────────
    @staticmethod
    async def get_by_id(db: AsyncSession, job_id: int) -> Job:
        """Lève NotFoundException si l'offre n'existe pas."""
        statement = select(Job).where(Job.id == job_id)
        result = await db.execute(statement)
        job = result.scalars().first()
        
        if not job:
            raise NotFoundException("Job", job_id)
        return job

    # ── READ ALL (ASYNC + paginé + filtres) ───────────────────────────────────
    @staticmethod
    async def get_all(
        db: AsyncSession,
        params: PaginationParams,
        keyword: Optional[str] = None,
        location: Optional[str] = None,
        contract_type: Optional[str] = None,
        experience_level: Optional[str] = None,
        work_mode: Optional[str] = None,
        skill: Optional[str] = None,
        status: Optional[str] = JobStatus.ACTIVE.value,
    ):
        """Liste paginée asynchrone avec filtres multiples."""
        query = select(Job)

        if status:
            query = query.where(Job.status == status)
        if contract_type:
            query = query.where(Job.contract_type == contract_type)
        if experience_level:
            query = query.where(Job.experience_level == experience_level)
        if work_mode:
            query = query.where(Job.work_mode == work_mode)
        if location:
            query = query.where(
                Job.location.ilike(f"%{location.strip()}%")
            )
        if keyword:
            term = f"%{keyword.strip()}%"
            query = query.where(
                or_(
                    Job.title.ilike(term),
                    Job.company.ilike(term),
                    Job.description.ilike(term),
                )
            )
        if skill:
            normalized = normalize_skill(skill)
            query = query.where(
                Job.required_skills.contains([normalized])
            )

        query = query.order_by(desc(Job.created_at))
        
        # Utilisation de la pagination asynchrone du projet
        return await paginate_query(db, query, params)

    # ── UPDATE (ASYNC) ────────────────────────────────────────────────────────
    @staticmethod
    async def update(db: AsyncSession, job_id: int, data: JobUpdate) -> Job:
        """Mise à jour partielle asynchrone d'une offre."""
        job = await JobService.get_by_id(db, job_id)
        update_data = data.model_dump(exclude_unset=True)

        # Convertir les enums en valeurs string
        for field in ["contract_type", "experience_level", "work_mode",
                      "degree_level", "status", "source"]:
            if field in update_data and update_data[field] is not None:
                if hasattr(update_data[field], "value"):
                    update_data[field] = update_data[field].value

        for field, value in update_data.items():
            setattr(job, field, value)

        await db.commit()
        await db.refresh(job)
        return job

    # ── DELETE (ASYNC) ────────────────────────────────────────────────────────
    @staticmethod
    async def delete(db: AsyncSession, job_id: int) -> dict:
        """Suppression définitive asynchrone d'une offre."""
        job = await JobService.get_by_id(db, job_id)
        title = job.title
        
        await db.delete(job)
        await db.commit()
        return {"message": f"Offre '{title}' supprimée avec succès."}

    # ── BULK CREATE (ASYNC - pour le module Imports) ──────────────────────────
    @staticmethod
    async def bulk_create(db: AsyncSession, jobs_data: list[JobCreate]) -> dict:
        """Insère une liste d'offres en une seule transaction asynchrone."""
        jobs = [
            Job(
                title=d.title,
                company=d.company,
                description=d.description,
                location=d.location,
                url=d.url,
                contract_type=d.contract_type.value,
                experience_level=d.experience_level.value,
                work_mode=d.work_mode.value,
                degree_level=d.degree_level.value if d.degree_level else None,
                required_skills=d.required_skills,
                salary_min=d.salary_min,
                salary_max=d.salary_max,
                salary_currency=d.salary_currency,
                status=d.status.value,
                source=d.source.value,
                published_at=d.published_at,
                expires_at=d.expires_at,
            )
            for d in jobs_data
        ]
        db.add_all(jobs)
        await db.commit()
        return {"created": len(jobs)}