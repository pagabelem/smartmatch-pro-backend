import os
import logging
from pathlib import Path
from typing import Optional

import aiofiles
from fastapi import Request, UploadFile

from app.core.exceptions import ValidationException, NotFoundException
from app.shared.utils import sanitize_filename, generate_uuid

logger = logging.getLogger(__name__)


class StorageService:
    """
    Service centralisé de gestion des fichiers.

    Toutes les opérations I/O sont asynchrones (aiofiles).
    Les chemins retournés sont toujours RELATIFS au base_dir
    (ne jamais exposer le chemin absolu serveur en BDD ou en réponse API).

    Architecture préparée pour S3 (v2) : les méthodes save(), delete(),
    get_url() pourront être surchargées dans une sous-classe S3StorageService
    sans changer les callers.

    Usage :
        storage = StorageService(
            base_dir=Path("storage"),
            allowed_extensions={".pdf", ".docx"},
            max_size=5 * 1024 * 1024,
        )
        relative_path = await storage.save_file(upload_file, subfolder="uploads/resumes/42")
    """

    def __init__(
        self,
        base_dir: Path,
        allowed_extensions: set[str],
        max_size: int,
    ) -> None:
        self.base_dir = base_dir.resolve()
        self.allowed_extensions = {ext.lower() for ext in allowed_extensions}
        self.max_size = max_size

    # ------------------------------------------------------------------
    # Validation
    # ------------------------------------------------------------------

    def validate_file(self, filename: str, file_size: int) -> None:
        """
        Valide l'extension et la taille d'un fichier AVANT écriture.
        Lève ValidationException si les contraintes ne sont pas respectées.
        """
        suffix = Path(filename).suffix.lower()
        if suffix not in self.allowed_extensions:
            raise ValidationException(
                f"Extension '{suffix}' non autorisée. "
                f"Extensions acceptées : {', '.join(sorted(self.allowed_extensions))}"
            )
        if file_size > self.max_size:
            max_mb = self.max_size / (1024 * 1024)
            actual_mb = file_size / (1024 * 1024)
            raise ValidationException(
                f"Fichier trop volumineux ({actual_mb:.1f} Mo). "
                f"Taille maximale : {max_mb:.0f} Mo."
            )

    # ------------------------------------------------------------------
    # Utilitaires internes
    # ------------------------------------------------------------------

    def ensure_directory_exists(self, subfolder: str) -> None:
        """Crée le sous-dossier dans base_dir si absent."""
        target = self.base_dir / subfolder
        target.mkdir(parents=True, exist_ok=True)

    def get_absolute_path(self, relative_path: str) -> Path:
        """
        Retourne le chemin absolu à partir d'un chemin relatif.
        Protège contre le path traversal (resolve + vérification préfixe).
        """
        absolute = (self.base_dir / relative_path).resolve()
        if not str(absolute).startswith(str(self.base_dir)):
            raise ValidationException("Chemin de fichier invalide (path traversal détecté).")
        return absolute

    def _build_filename(
        self,
        original_filename: str,
        custom_filename: Optional[str] = None,
    ) -> str:
        """
        Construit le nom de fichier final :
        - si custom_filename fourni → sanitize + garder extension originale
        - sinon → UUID + extension originale (évite les collisions)
        """
        suffix = Path(original_filename).suffix.lower()
        if custom_filename:
            base = sanitize_filename(Path(custom_filename).stem)
            return f"{base}{suffix}"
        return f"{generate_uuid()}{suffix}"

    # ------------------------------------------------------------------
    # Opérations principales
    # ------------------------------------------------------------------

    async def save_file(
        self,
        file: UploadFile,
        subfolder: str,
        custom_filename: Optional[str] = None,
    ) -> str:
        """
        Sauvegarde un UploadFile dans base_dir/subfolder.

        Étapes :
        1. Lecture du contenu en mémoire (pour valider la taille réelle)
        2. Validation extension + taille
        3. Création du sous-dossier si absent
        4. Écriture asynchrone avec aiofiles

        Retourne le chemin RELATIF (ex: uploads/resumes/42/uuid.pdf).
        Ce chemin est destiné à être stocké en BDD.
        """
        content = await file.read()
        file_size = len(content)

        original_name = file.filename or "upload"
        self.validate_file(original_name, file_size)

        self.ensure_directory_exists(subfolder)

        final_filename = self._build_filename(original_name, custom_filename)
        relative_path = f"{subfolder}/{final_filename}"
        absolute_path = self.get_absolute_path(relative_path)

        async with aiofiles.open(absolute_path, "wb") as f:
            await f.write(content)

        logger.info("Fichier sauvegardé : %s (%d octets)", relative_path, file_size)
        return relative_path

    async def delete_file(self, relative_path: str) -> bool:
        """
        Supprime physiquement un fichier.
        Retourne True si supprimé, lève NotFoundException si introuvable.
        """
        absolute_path = self.get_absolute_path(relative_path)

        if not absolute_path.exists():
            raise NotFoundException(f"Fichier introuvable : {relative_path}")

        try:
            os.remove(absolute_path)
            logger.info("Fichier supprimé : %s", relative_path)

            # Suppression du dossier parent s'il est vide (nettoyage)
            parent = absolute_path.parent
            if parent != self.base_dir and not any(parent.iterdir()):
                parent.rmdir()

            return True
        except OSError as exc:
            logger.error("Erreur suppression fichier %s : %s", relative_path, exc)
            raise

    def get_file_url(self, relative_path: str, request: Request) -> str:
        """
        Génère l'URL publique d'accès au fichier via la route storage.

        L'URL générée pointe vers GET /api/v1/storage/{relative_path}.
        En v2 (S3), cette méthode retournera une pre-signed URL.
        """
        base_url = str(request.base_url).rstrip("/")
        encoded_path = relative_path.replace(" ", "%20")
        return f"{base_url}/api/v1/storage/{encoded_path}"

    def get_file_info(self, relative_path: str) -> dict:
        """
        Retourne les métadonnées d'un fichier (taille, existence).
        Utile pour les réponses d'upload.
        """
        absolute_path = self.get_absolute_path(relative_path)
        if not absolute_path.exists():
            raise NotFoundException(f"Fichier introuvable : {relative_path}")
        stat = absolute_path.stat()
        return {
            "filename": absolute_path.name,
            "size": stat.st_size,
            "exists": True,
        }


# ---------------------------------------------------------------------------
# Instance partagée (singleton) — configurée depuis app/config.py
# ---------------------------------------------------------------------------

def create_storage_service() -> "StorageService":
    """
    Factory qui lit la configuration depuis settings.
    Appelée une seule fois au démarrage (ou lors du premier import).
    """
    from app.config import settings

    allowed_ext = set(
        getattr(settings, "ALLOWED_EXTENSIONS", [".pdf", ".docx", ".doc", ".png", ".jpg", ".jpeg"])
    )
    max_size = int(getattr(settings, "MAX_FILE_SIZE", 5 * 1024 * 1024))
    storage_dir = Path(getattr(settings, "STORAGE_DIR", "storage"))

    return StorageService(
        base_dir=storage_dir,
        allowed_extensions=allowed_ext,
        max_size=max_size,
    )


# Instance globale — import direct dans les autres modules
storage_service = create_storage_service()