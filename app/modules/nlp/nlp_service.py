import time
import logging
from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.modules.nlp.text_cleaner import clean_text
from app.modules.nlp.skill_extractor import extract_skills_from_text, get_nlp_model
from app.modules.resumes.resume_model import Resume
from app.modules.users.user_model import Profile  # ✅ CORRIGÉ (Profile est dans users.user_model)
from app.core.exceptions import NotFoundException

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Initialisation du modèle spaCy au démarrage (appelé depuis lifespan)
# ---------------------------------------------------------------------------

def preload_nlp_model() -> None:
    """
    Charge le modèle spaCy une seule fois au démarrage de l'application.
    À appeler depuis le lifespan context manager de FastAPI dans main.py :

        @asynccontextmanager
        async def lifespan(app: FastAPI):
            preload_nlp_model()
            yield
    """
    logger.info("Chargement du modèle spaCy...")
    get_nlp_model()
    logger.info("Modèle spaCy chargé.")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

async def _get_resume_with_profile(
    resume_id: int,
    db: AsyncSession,
) -> Resume:
    """Récupère un CV avec son profil associé via selectinload."""
    result = await db.execute(
        select(Resume)
        .options(selectinload(Resume.profile))
        .where(Resume.id == resume_id)
    )
    resume = result.scalar_one_or_none()
    if resume is None:
        raise NotFoundException(message=f"CV introuvable (id={resume_id})")
    return resume


async def _get_profile(profile_id: int, db: AsyncSession) -> Profile:
    """Récupère un profil par son ID."""
    result = await db.execute(
        select(Profile).where(Profile.id == profile_id)
    )
    profile = result.scalar_one_or_none()
    if profile is None:
        raise NotFoundException(message=f"Profil introuvable (id={profile_id})")
    return profile


def _merge_skills(existing: Optional[list], new_skills: list[str]) -> list[str]:
    """
    Fusionne les compétences existantes avec les nouvelles.
    Dédoublonne et trie le résultat.
    """
    existing_set = set(existing) if existing else set()
    merged = existing_set | set(new_skills)
    return sorted(merged)


# ---------------------------------------------------------------------------
# Service functions
# ---------------------------------------------------------------------------

async def process_resume(resume_id: int, db: AsyncSession) -> dict:
    """
    Traite un CV spécifique :
    1. Récupère le raw_text
    2. Nettoie le texte
    3. Extrait les compétences
    4. Met à jour Profile.skills_extracted
    5. Marque Resume.is_parsed = True

    Retourne un dict compatible avec NLPProcessResponse.
    """
    start = time.perf_counter()

    resume = await _get_resume_with_profile(resume_id, db)

    if not resume.raw_text:
        return {
            "resume_id": resume_id,
            "skills_extracted": [],
            "processing_time_ms": 0,
            "status": "error",
            "message": "Le CV n'a pas de texte brut disponible (raw_text vide).",
        }

    # Nettoyage
    cleaned = clean_text(resume.raw_text)

    # Extraction
    skills = extract_skills_from_text(cleaned)

    # Mise à jour du profil
    profile = resume.profile
    profile.skills_extracted = _merge_skills(profile.skills_extracted, skills)

    # Marquage du CV
    resume.is_parsed = True

    await db.commit()
    await db.refresh(resume)
    await db.refresh(profile)

    elapsed_ms = int((time.perf_counter() - start) * 1000)
    logger.info(
        "CV %s traité — %d compétences extraites en %dms",
        resume_id, len(skills), elapsed_ms,
    )

    return {
        "resume_id": resume_id,
        "skills_extracted": skills,
        "processing_time_ms": elapsed_ms,
        "status": "success",
        "message": None,
    }


async def bulk_process_resumes(profile_id: int, db: AsyncSession) -> dict:
    """
    Traite tous les CVs non encore parsés d'un profil.
    Retourne un résumé du traitement.
    """
    start = time.perf_counter()

    await _get_profile(profile_id, db)  # Vérification existence profil

    result = await db.execute(
        select(Resume).where(
            Resume.profile_id == profile_id,
            Resume.is_parsed == False,  # noqa: E712
        )
    )
    resumes = result.scalars().all()

    processed = 0
    all_new_skills: set[str] = set()

    for resume in resumes:
        try:
            res = await process_resume(resume.id, db)
            if res["status"] == "success":
                processed += 1
                all_new_skills.update(res["skills_extracted"])
        except Exception as exc:
            logger.warning("Erreur traitement CV %s : %s", resume.id, exc)

    # Compte des CVs déjà parsés (skipped)
    total_result = await db.execute(
        select(Resume).where(Resume.profile_id == profile_id)
    )
    total_resumes = len(total_result.scalars().all())
    skipped = total_resumes - len(resumes)

    elapsed_ms = int((time.perf_counter() - start) * 1000)

    return {
        "profile_id": profile_id,
        "processed": processed,
        "skipped": skipped,
        "total_skills": len(all_new_skills),
        "processing_time_ms": elapsed_ms,
        "status": "success",
    }


async def get_nlp_status(resume_id: int, db: AsyncSession) -> dict:
    """Retourne l'état du parsing NLP d'un CV."""
    result = await db.execute(
        select(Resume).where(Resume.id == resume_id)
    )
    resume = result.scalar_one_or_none()
    if resume is None:
        raise NotFoundException(message=f"CV introuvable (id={resume_id})")

    return {
        "resume_id": resume_id,
        "is_parsed": resume.is_parsed,
        "processed_at": resume.updated_at if resume.is_parsed else None,
        "raw_text_length": len(resume.raw_text) if resume.raw_text else 0,
    }


async def get_profile_skills(profile_id: int, db: AsyncSession) -> dict:
    """Retourne les compétences extraites d'un profil."""
    profile = await _get_profile(profile_id, db)
    skills = profile.skills_extracted or []
    return {
        "profile_id": profile_id,
        "skills": skills,
        "total": len(skills),
    }


def extract_text_debug(text: str) -> list[str]:
    """
    Extraction synchrone sur texte libre (endpoint debug).
    Nettoie puis extrait les compétences sans accès BDD.
    """
    cleaned = clean_text(text)
    return extract_skills_from_text(cleaned)