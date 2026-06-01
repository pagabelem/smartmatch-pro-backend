# tests/test_skill_gap.py

import pytest
from sqlalchemy.orm import Session

from app.modules.skill_gap.skill_gap_service import SkillGapService
from app.modules.jobs.job_schema import JobCreate
from app.modules.jobs.job_service import JobService
from app.modules.users.user_model import User, Profile
from app.shared.enums import ContractType, ExperienceLevel, WorkMode


# ── Fixtures ──────────────────────────────────────────────────────────────────
def create_test_user(db: Session, email: str = "test@test.com") -> User:
    user = User(
        email=email,
        hashed_password="hashed_password_test",
        is_active=True,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def create_test_profile(
    db: Session,
    user_id: int,
    skills: list
) -> Profile:
    profile = Profile(
        user_id=user_id,
        first_name="Test",
        last_name="User",
        skills_raw=skills,
        skills_extracted={"hard_skills": [], "soft_skills": []},
    )
    db.add(profile)
    db.commit()
    db.refresh(profile)
    return profile


def create_test_job(
    db: Session,
    title: str,
    skills: list
) -> object:
    return JobService.create(db, JobCreate(
        title=title,
        company="TestCorp",
        contract_type=ContractType.CDI,
        experience_level=ExperienceLevel.MID,
        work_mode=WorkMode.HYBRID,
        required_skills=skills,
    ))


# ── Tests ANALYZE FOR JOB ─────────────────────────────────────────────────────
def test_skill_gap_perfect_match(db: Session):
    """Profil couvre 100% des skills du job."""
    user = create_test_user(db)
    create_test_profile(db, user.id, skills=["python", "sql", "fastapi"])
    job = create_test_job(db, "Dev Python", ["python", "sql", "fastapi"])

    gap = SkillGapService.analyze_for_job(db, user.id, job.id)

    assert gap.coverage_percent == 100
    assert len(gap.missing_skills) == 0
    assert set(gap.matching_skills) == {"python", "sql", "fastapi"}
    print("✅ test_skill_gap_perfect_match OK")


def test_skill_gap_no_match(db: Session):
    """Profil n'a aucune skill du job."""
    user = create_test_user(db)
    create_test_profile(db, user.id, skills=["java", "spring"])
    job = create_test_job(db, "Dev Python", ["python", "fastapi", "sql"])

    gap = SkillGapService.analyze_for_job(db, user.id, job.id)

    assert gap.coverage_percent == 0
    assert len(gap.matching_skills) == 0
    assert set(gap.missing_skills) == {"python", "fastapi", "sql"}
    print("✅ test_skill_gap_no_match OK")


def test_skill_gap_partial_match(db: Session):
    """Profil couvre une partie des skills du job."""
    user = create_test_user(db)
    create_test_profile(db, user.id, skills=["python", "sql"])
    job = create_test_job(
        db, "Dev Python",
        ["python", "sql", "docker", "kubernetes"]
    )

    gap = SkillGapService.analyze_for_job(db, user.id, job.id)

    assert gap.coverage_percent == 50
    assert set(gap.matching_skills) == {"python", "sql"}
    assert set(gap.missing_skills) == {"docker", "kubernetes"}
    print("✅ test_skill_gap_partial_match OK")


def test_skill_gap_extra_skills(db: Session):
    """Le profil a des skills supplémentaires non requises par le job."""
    user = create_test_user(db)
    create_test_profile(
        db, user.id,
        skills=["python", "sql", "react", "vue"]
    )
    job = create_test_job(db, "Dev Python", ["python", "sql"])

    gap = SkillGapService.analyze_for_job(db, user.id, job.id)

    assert gap.coverage_percent == 100
    assert set(gap.extra_skills) == {"react", "vue"}
    print("✅ test_skill_gap_extra_skills OK")


def test_skill_gap_no_profile(db: Session):
    """Sans profil → ValueError."""
    user = create_test_user(db)
    job = create_test_job(db, "Dev Python", ["python"])

    with pytest.raises(ValueError, match="profil"):
        SkillGapService.analyze_for_job(db, user.id, job.id)
    print("✅ test_skill_gap_no_profile OK")


def test_skill_gap_job_not_found(db: Session):
    """Job inexistant → ValueError."""
    user = create_test_user(db)
    create_test_profile(db, user.id, skills=["python"])

    with pytest.raises(ValueError, match="introuvable"):
        SkillGapService.analyze_for_job(db, user.id, 9999)
    print("✅ test_skill_gap_job_not_found OK")


# ── Tests ANALYZE GLOBAL ──────────────────────────────────────────────────────
def test_skill_gap_global_no_jobs(db: Session):
    """Pas d'offres actives → résumé vide."""
    user = create_test_user(db)
    create_test_profile(db, user.id, skills=["python"])

    result = SkillGapService.analyze_global(db, user.id)

    assert result["total_jobs_analyzed"] == 0
    assert result["average_coverage_percent"] == 0
    print("✅ test_skill_gap_global_no_jobs OK")


def test_skill_gap_global_with_jobs(db: Session):
    """Analyse globale sur plusieurs offres."""
    user = create_test_user(db)
    create_test_profile(
        db, user.id,
        skills=["python", "sql", "fastapi"]
    )
    create_test_job(db, "Job 1", ["python", "sql", "docker"])
    create_test_job(db, "Job 2", ["python", "fastapi", "react"])
    create_test_job(db, "Job 3", ["java", "spring", "mysql"])

    result = SkillGapService.analyze_global(db, user.id)

    assert result["total_jobs_analyzed"] == 3
    assert result["average_coverage_percent"] >= 0
    assert isinstance(result["top_missing_skills"], list)
    print("✅ test_skill_gap_global_with_jobs OK")


# ── Tests HISTORY ─────────────────────────────────────────────────────────────
def test_skill_gap_history(db: Session):
    """L'historique retourne les analyses passées."""
    from app.shared.pagination import PaginationParams

    user = create_test_user(db)
    create_test_profile(db, user.id, skills=["python", "sql"])
    job1 = create_test_job(db, "Job 1", ["python", "docker"])
    job2 = create_test_job(db, "Job 2", ["sql", "mongodb"])

    SkillGapService.analyze_for_job(db, user.id, job1.id)
    SkillGapService.analyze_for_job(db, user.id, job2.id)

    params = PaginationParams(page=1, page_size=10)
    page = SkillGapService.get_history(db, user.id, params)

    assert page.total == 2
    print("✅ test_skill_gap_history OK")