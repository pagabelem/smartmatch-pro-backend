# tests/test_jobs.py

import pytest
from sqlalchemy.orm import Session

from app.modules.jobs.job_model import Job
from app.modules.jobs.job_schema import JobCreate, JobUpdate
from app.modules.jobs.job_service import JobService
from app.shared.enums import ContractType, ExperienceLevel, JobStatus, WorkMode


# ── Fixtures ──────────────────────────────────────────────────────────────────
def make_job_create(**kwargs) -> JobCreate:
    defaults = {
        "title": "Développeur Python",
        "company": "TechCorp",
        "description": "Développement d'APIs FastAPI",
        "location": "Casablanca",
        "contract_type": ContractType.CDI,
        "experience_level": ExperienceLevel.MID,
        "work_mode": WorkMode.HYBRID,
        "required_skills": ["python", "fastapi", "postgresql"],
        "salary_min": 10000.0,
        "salary_max": 20000.0,
    }
    defaults.update(kwargs)
    return JobCreate(**defaults)


# ── Tests CREATE ──────────────────────────────────────────────────────────────
def test_create_job(db: Session):
    """Un job créé doit être récupérable par son ID."""
    data = make_job_create()
    job = JobService.create(db, data)

    assert job.id is not None
    assert job.title == "Développeur Python"
    assert job.company == "TechCorp"
    assert job.status == "active"
    assert "python" in job.required_skills
    print("✅ test_create_job OK")


def test_create_job_normalizes_skills(db: Session):
    """Les skills doivent être normalisées en lowercase."""
    data = make_job_create(required_skills=["Python", "  FastAPI  ", "SQL"])
    job = JobService.create(db, data)

    assert "python" in job.required_skills
    assert "fastapi" in job.required_skills
    assert "sql" in job.required_skills
    print("✅ test_create_job_normalizes_skills OK")


# ── Tests READ ────────────────────────────────────────────────────────────────
def test_get_job_by_id(db: Session):
    """Récupérer un job par son ID."""
    job = JobService.create(db, make_job_create())
    fetched = JobService.get_by_id(db, job.id)

    assert fetched.id == job.id
    assert fetched.title == job.title
    print("✅ test_get_job_by_id OK")


def test_get_job_not_found(db: Session):
    """Un ID inexistant doit lever une exception."""
    from app.core.exceptions import NotFoundException
    with pytest.raises(NotFoundException):
        JobService.get_by_id(db, 9999)
    print("✅ test_get_job_not_found OK")


def test_get_all_jobs(db: Session):
    """Lister tous les jobs avec pagination."""
    from app.shared.pagination import PaginationParams
    JobService.create(db, make_job_create(title="Job 1"))
    JobService.create(db, make_job_create(title="Job 2"))
    JobService.create(db, make_job_create(title="Job 3"))

    params = PaginationParams(page=1, page_size=10)
    page = JobService.get_all(db, params)

    assert page.total == 3
    assert len(page.items) == 3
    print("✅ test_get_all_jobs OK")


def test_get_all_jobs_filter_by_location(db: Session):
    """Filtrer les jobs par localisation."""
    from app.shared.pagination import PaginationParams
    JobService.create(db, make_job_create(title="Job Casablanca", location="Casablanca"))
    JobService.create(db, make_job_create(title="Job Rabat", location="Rabat"))

    params = PaginationParams(page=1, page_size=10)
    page = JobService.get_all(db, params, location="Casablanca")

    assert page.total == 1
    assert page.items[0].location == "Casablanca"
    print("✅ test_get_all_jobs_filter_by_location OK")


# ── Tests UPDATE ──────────────────────────────────────────────────────────────
def test_update_job(db: Session):
    """Mettre à jour un job existant."""
    job = JobService.create(db, make_job_create())
    updated = JobService.update(
        db, job.id,
        JobUpdate(title="Senior Python Developer", salary_max=30000.0)
    )

    assert updated.title == "Senior Python Developer"
    assert updated.salary_max == 30000.0
    print("✅ test_update_job OK")


# ── Tests DELETE ──────────────────────────────────────────────────────────────
def test_delete_job(db: Session):
    """Supprimer un job."""
    from app.core.exceptions import NotFoundException
    job = JobService.create(db, make_job_create())
    job_id = job.id

    JobService.delete(db, job_id)

    with pytest.raises(NotFoundException):
        JobService.get_by_id(db, job_id)
    print("✅ test_delete_job OK")


# ── Tests BULK CREATE ─────────────────────────────────────────────────────────
def test_bulk_create_jobs(db: Session):
    """Créer plusieurs jobs en une seule opération."""
    jobs_data = [
        make_job_create(title=f"Job {i}") for i in range(5)
    ]
    JobService.bulk_create(db, jobs_data)

    from app.shared.pagination import PaginationParams
    page = JobService.get_all(db, PaginationParams(page=1, page_size=20))

    assert page.total == 5
    print("✅ test_bulk_create_jobs OK")