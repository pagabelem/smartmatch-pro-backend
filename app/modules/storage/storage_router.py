import re
import logging
from pathlib import Path

from fastapi import APIRouter, Depends, Request
from fastapi.responses import FileResponse
from sqlalchemy import select

from app.modules.auth.dependencies import get_current_user
from app.modules.users.user_model import User, Profile
from app.modules.storage.storage_service import storage_service
from app.modules.storage.storage_schema import FileDeleteResponse
from app.core.exceptions import NotFoundException, ForbiddenException
from app.database import get_db
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/storage", tags=["Storage"])

# Regex pour détecter les chemins de CVs : uploads/resumes/{profile_id}/...
_RESUME_PATH_RE = re.compile(r"^uploads/resumes/(\d+)/")


def _extract_profile_id_from_path(file_path: str) -> int | None:
    """
    Si le chemin concerne un CV (uploads/resumes/{id}/...),
    retourne le profile_id, sinon None.
    """
    match = _RESUME_PATH_RE.match(file_path)
    return int(match.group(1)) if match else None


async def _check_file_access(
    file_path: str,
    current_user: User,
    db: AsyncSession,
) -> None:
    """
    Vérifie que l'utilisateur a le droit d'accéder au fichier.

    Règles :
    - Admin → accès total
    - Chemin resumes/{profile_id}/ → propriétaire du profil uniquement
    - Autre chemin → admin uniquement
    """
    if current_user.is_superuser:
        return

    profile_id = _extract_profile_id_from_path(file_path)

    if profile_id is None:
        # Chemin non reconnu → admin only
        raise ForbiddenException("Accès réservé aux administrateurs.")

    # Vérification propriétaire du profil
    result = await db.execute(
        select(Profile).where(Profile.id == profile_id)
    )
    profile = result.scalar_one_or_none()

    if profile is None:
        raise NotFoundException("Profil associé au fichier introuvable.")

    if profile.user_id != current_user.id:
        raise ForbiddenException("Vous n'êtes pas autorisé à accéder à ce fichier.")


# ---------------------------------------------------------------------------
# GET /storage/{file_path:path}
# ---------------------------------------------------------------------------

@router.get(
    "/{file_path:path}",
    summary="Servir un fichier uploadé",
    description=(
        "Retourne le fichier correspondant au chemin relatif. "
        "Vérifie que l'utilisateur est propriétaire du profil associé (ou admin). "
        "Ne jamais exposer le chemin absolu serveur."
    ),
)
async def serve_file(
    file_path: str,
    request: Request,
    current_user: User = Depends(get_current_user),
):
    # Ouverture d'une session DB pour la vérification des droits
    async for db in get_db():
        await _check_file_access(file_path, current_user, db)
        break

    absolute_path = storage_service.get_absolute_path(file_path)

    if not absolute_path.exists():
        raise NotFoundException(f"Fichier introuvable : {file_path}")

    # Déduction du media_type depuis l'extension
    suffix = absolute_path.suffix.lower()
    media_type_map = {
        ".pdf": "application/pdf",
        ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        ".doc": "application/msword",
        ".png": "image/png",
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
    }
    media_type = media_type_map.get(suffix, "application/octet-stream")

    logger.info(
        "Fichier servi : %s → user_id=%s", file_path, current_user.id
    )

    return FileResponse(
        path=str(absolute_path),
        media_type=media_type,
        filename=absolute_path.name,
    )


# ---------------------------------------------------------------------------
# DELETE /storage/{file_path:path}
# ---------------------------------------------------------------------------

@router.delete(
    "/{file_path:path}",
    response_model=FileDeleteResponse,
    summary="Supprimer un fichier (admin uniquement)",
)
async def delete_file(
    file_path: str,
    current_user: User = Depends(get_current_user),
) -> FileDeleteResponse:
    if not current_user.is_superuser:
        raise ForbiddenException("Seuls les administrateurs peuvent supprimer des fichiers.")

    filename = Path(file_path).name
    await storage_service.delete_file(file_path)

    logger.warning(
        "Fichier supprimé par admin : %s (admin_id=%s)", file_path, current_user.id
    )

    return FileDeleteResponse(
        filename=filename,
        relative_path=file_path,
        deleted=True,
        message=f"Fichier '{filename}' supprimé avec succès.",
    )