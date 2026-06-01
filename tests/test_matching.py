# tests/test_matching.py

import pytest
from sqlalchemy.orm import Session

from app.modules.matching.cosine_matcher import cosine_similarity
from app.modules.matching.matching_service import MatchingService
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


# ── Tests COSINE SIMILARITY ───────────────────────────────────────────────────
def test_cosine_identical_skills():
    """Deux listes identiques → score = 1.0."""
    score = cosine_similarity(
        ["python", "sql", "fastapi"],
        ["python", "sql", "fastapi"]
    )
    assert score == 1.0
    print("✅ test_cosine_identical_skills OK")


def test_cosine_no_common_skills():
    """Aucune compétence en commun → score = 0.0."""
    score = cosine_similarity(
        ["python", "sql"],
        ["java", "spring"]
    )
    assert score == 0.0
    print("✅ test_cosine_no_common_skills OK")


def test_cosine_partial_match():
    """Correspondance partielle → score entre 0 et 1."""
    score = cosine_similarity(
        ["python", "sql", "fastapi"],
        ["python", "docker", "fastapi"]
    )
    assert 0.0 < score < 1.0
    assert score == pytest.approx(0.6667, rel=1e-3)
    print("✅ test_cosine_partial_match OK")


def test_cosine_empty_lists():
    """Listes vides → score = 0.0."""
    assert cosine_similarity([], ["python"]) == 0.0
    assert cosine_similarity(["python"], []) == 0.0
    assert cosine_similarity([], []) == 0.0
    print("✅ test_cosine_empty_lists OK")


def test_cosine_case_insensitive():
    """La comparaison est insensible à la casse."""
    score = cosine_similarity(
        ["Python", "SQL"],
        ["python", "sql"]
    )
    assert score == 1.0
    print("✅ test_cosine_case_insensitive OK")


# ── Tests MATCHING SERVICE ────────────────────────────────────────────────────
def test_run_matching_no_profile(db: Session):
    """Sans profil → ValueError."""
    with pytest.raises(ValueError, match="Aucun profil"):
        MatchingService.run_matching(db, user_id=9999)
    print("✅ test_run_matching_no_profile OK")


def test_run_matching_no_skills(db: Session):
    """Profil sans compétences → ValueError."""
    user = create_test_user(db)
    create_test_profile(db, user.id, skills=[])

    with pytest.raises(ValueError, match="compétence"):
        MatchingService.run_matching(db, user_id=user.id)
    print("✅ test_run_matching_no_skills OK")


def test_run_matching_no_jobs(db: Session):
    """Pas d'offres actives → 0 recommandations."""
    user = create_test_user(db)
    create_test_profile(db, user.id, skills=["python", "sql"])

    result = MatchingService.run_matching(db, user_id=user.id)

    assert result["total_jobs_evaluated"] == 0
    assert result["recommendations_saved"] == 0
    print("✅ test_run_matching_no_jobs OK")


def test_run_matching_with_jobs(db: Session):
    """Matching complet avec profil et offres."""
    user = create_test_user(db)
    create_test_profile(db, user.id, skills=["python", "fastapi", "sql"])

    create_test_job(db, "Dev Python", ["python", "fastapi", "postgresql"])
    create_test_job(db, "Dev Java", ["java", "spring", "mysql"])
    create_test_job(db, "Data Engineer", ["python", "sql", "spark"])

    result = MatchingService.run_matching(db, user_id=user.id)

    assert result["total_jobs_evaluated"] == 3
    assert result["recommendations_saved"] >= 1
    assert result["top_score"] > 0.0
    print("✅ test_run_matching_with_jobs OK")


def test_run_matching_score_labels(db: Session):
    """Les labels de score sont correctement assignés."""
    from app.modules.matching.recommendation_model import Recommendation

    user = create_test_user(db)
    create_test_profile(
        db, user.id,
        skills=["python", "fastapi", "sql", "docker", "postgresql"]
    )
    create_test_job(
        db, "Dev Python Senior",
        ["python", "fastapi", "sql", "docker", "postgresql"]
    )

    MatchingService.run_matching(db, user_id=user.id)

    recs = db.query(Recommendation).filter(
        Recommendation.user_id == user.id
    ).all()

    assert len(recs) == 1
    assert recs[0].score == 1.0
    assert recs[0].score_label == "Excellent"
    print("✅ test_run_matching_score_labels OK")