"""
app/modules/resumes/resume_service.py
Services métier pour le module Resumes :
  - Validation, sauvegarde physique (aiofiles), extraction texte
  - CRUD base de données
  - Suppression en cascade (fichier + BDD)
"""

import os
import math
import logging
from pathlib import Path

import aiofiles
from fastapi import UploadFile
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.core.exceptions import NotFoundException, ValidationException
from app.modules.resumes.resume_model import Resume
from app.modules.resumes.file_parser import parse_resume_file
from app.shared.utils import sanitize_filename, generate_uuid

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constantes MIME
# ---------------------------------------------------------------------------
EXTENSION_TO_MIME: dict[str, str] = {
    "pdf": "application/pdf",
    "docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
}


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------

def _get_extension(filename: str) -> str:
    return Path(filename).suffix.lstrip(".").lower()


def _validate_file(filename: str, file_size: int) -> None:
    """Valide l'extension et la taille AVANT toute écriture disque."""
    ext = _get_extension(filename)
    allowed: set[str] = settings.allowed_resume_extensions_set

    if ext not in allowed:
        raise ValidationException(
            f"Extension '.{ext}' non autorisée. "
            f"Extensions acceptées : {', '.join(sorted(allowed))}"
        )

    if file_size > settings.max_file_size_bytes:
        max_mb = settings.MAX_FILE_SIZE_MB
        raise ValidationException(
            f"Fichier trop volumineux ({file_size / 1_048_576:.1f} Mo). "
            f"Taille maximale : {max_mb} Mo."
        )


# ---------------------------------------------------------------------------
# Sauvegarde physique
# ---------------------------------------------------------------------------

async def save_resume_file(
    file: UploadFile, profile_id: int
) -> tuple[str, int, str]:
    """Lit, valide et sauvegarde le fichier CV sur disque.

    Returns:
        Tuple (relative_file_path, file_size_bytes, mime_type)

    Raises:
        ValidationException: extension ou taille invalide.
    """
    content: bytes = await file.read()
    file_size = len(content)

    original_name = file.filename or "resume"
    _validate_file(original_name, file_size)

    ext = _get_extension(original_name)
    mime_type = EXTENSION_TO_MIME[ext]

    # Nom de fichier unique sur disque
    safe_name = sanitize_filename(Path(original_name).stem)
    unique_name = f"{safe_name}_{generate_uuid()}.{ext}"

    # Chemin relatif stocké en BDD
    relative_path = f"resumes/{profile_id}/{unique_name}"
    absolute_path = Path(settings.UPLOAD_DIR) / relative_path

    # Création du dossier si nécessaire
    absolute_path.parent.mkdir(parents=True, exist_ok=True)

    async with aiofiles.open(absolute_path, "wb") as out_file:
        await out_file.write(content)

    logger.info(
        "CV sauvegardé : %s (%d octets)", relative_path, file_size
    )
    return relative_path, file_size, mime_type


# ---------------------------------------------------------------------------
# Extraction de texte
# ---------------------------------------------------------------------------

def extract_raw_text(absolute_path: str, mime_type: str) -> str | None:
    """Tente l'extraction synchrone du texte brut. Retourne None en cas d'échec."""
    try:
        return parse_resume_file(absolute_path, mime_type)
    except Exception as exc:
        logger.warning("Extraction texte échouée pour %s : %s", absolute_path, exc)
        return None


# ---------------------------------------------------------------------------
# CRUD Base de données
# ---------------------------------------------------------------------------

async def create_resume_record(
    db: AsyncSession,
    profile_id: int,
    filename: str,
    file_path: str,
    file_size: int,
    mime_type: str,
    raw_text: str | None,
) -> Resume:
    """Insère un enregistrement Resume en base."""
    resume = Resume(
        profile_id=profile_id,
        filename=filename,
        file_path=file_path,
        file_size=file_size,
        mime_type=mime_type,
        raw_text=raw_text,
        is_parsed=raw_text is not None,
    )
    db.add(resume)
    await db.commit()
    await db.refresh(resume)
    logger.info("Resume#%d créé en BDD pour profile#%d", resume.id, profile_id)
    return resume


async def get_resume_by_id(db: AsyncSession, resume_id: int) -> Resume:
    """Récupère un Resume par son ID. Lève NotFoundException si absent."""
    result = await db.execute(select(Resume).where(Resume.id == resume_id))
    resume = result.scalar_one_or_none()
    if resume is None:
        raise NotFoundException(f"CV introuvable (id={resume_id})")
    return resume


async def get_resumes_by_profile(
    db: AsyncSession,
    profile_id: int,
    page: int = 1,
    limit: int = 10,
) -> tuple[list[Resume], int]:
    """Liste paginée des CVs d'un profil.

    Returns:
        Tuple (items, total_count)
    """
    offset = (page - 1) * limit

    count_result = await db.execute(
        select(func.count()).where(Resume.profile_id == profile_id)
    )
    total = count_result.scalar_one()

    items_result = await db.execute(
        select(Resume)
        .where(Resume.profile_id == profile_id)
        .order_by(Resume.created_at.desc())
        .offset(offset)
        .limit(limit)
    )
    items = list(items_result.scalars().all())
    return items, total


async def get_latest_resume(
    db: AsyncSession, profile_id: int
) -> Resume | None:
    """Retourne le CV le plus récent d'un profil, ou None."""
    result = await db.execute(
        select(Resume)
        .where(Resume.profile_id == profile_id)
        .order_by(Resume.created_at.desc())
        .limit(1)
    )
    return result.scalar_one_or_none()


async def delete_resume(db: AsyncSession, resume_id: int) -> None:
    """Supprime le fichier physique puis l'enregistrement BDD.

    Raises:
        NotFoundException: si le CV n'existe pas.
    """
    resume = await get_resume_by_id(db, resume_id)

    # Suppression physique
    absolute_path = Path(settings.UPLOAD_DIR) / resume.file_path
    if absolute_path.exists():
        try:
            os.remove(absolute_path)
            logger.info("Fichier supprimé : %s", absolute_path)
        except OSError as exc:
            logger.warning("Impossible de supprimer le fichier %s : %s", absolute_path, exc)
    else:
        logger.warning("Fichier physique déjà absent : %s", absolute_path)

    # Suppression BDD
    await db.delete(resume)
    await db.commit()
    logger.info("Resume#%d supprimé de la BDD", resume_id)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def compute_pages(total: int, limit: int) -> int:
    return math.ceil(total / limit) if limit > 0 else 0