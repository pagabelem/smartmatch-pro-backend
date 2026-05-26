"""
app/modules/resumes/file_parser.py
Parser multi-format : dispatche selon le mime_type et extrait le texte brut.
Nettoyage basique avant stockage (espaces, caractères de contrôle).
"""

import re
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

MIME_PDF = "application/pdf"
MIME_DOCX = (
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
)


def _clean_text(text: str) -> str:
    """Nettoyage basique du texte extrait.

    - Supprime les caractères de contrôle (sauf newline/tab)
    - Normalise les espaces multiples
    - Supprime les lignes vides en excès (> 2 consécutives)
    - Strip global
    """
    # Retirer les caractères de contrôle sauf \n et \t
    text = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]", "", text)
    # Normaliser les espaces (pas les newlines)
    text = re.sub(r"[ \t]+", " ", text)
    # Réduire les lignes vides excessives
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def _extract_text_from_pdf(file_path: str) -> str:
    """Extraction du texte depuis un PDF avec pypdf (ou PyPDF2 en fallback)."""
    text_parts: list[str] = []

    try:
        # Essai avec pypdf (successeur moderne de PyPDF2)
        import pypdf  # type: ignore

        with open(file_path, "rb") as f:
            reader = pypdf.PdfReader(f)
            for page in reader.pages:
                page_text = page.extract_text() or ""
                text_parts.append(page_text)
        logger.debug("PDF parsé avec pypdf : %s (%d pages)", file_path, len(reader.pages))

    except ImportError:
        try:
            import PyPDF2  # type: ignore

            with open(file_path, "rb") as f:
                reader = PyPDF2.PdfReader(f)
                for page in reader.pages:
                    page_text = page.extract_text() or ""
                    text_parts.append(page_text)
            logger.debug("PDF parsé avec PyPDF2 : %s", file_path)

        except ImportError as exc:
            raise ImportError(
                "Aucun parser PDF disponible. Installer pypdf : pip install pypdf"
            ) from exc

    return "\n".join(text_parts)


def _extract_text_from_docx(file_path: str) -> str:
    """Extraction du texte depuis un fichier DOCX avec python-docx."""
    try:
        from docx import Document  # type: ignore
    except ImportError as exc:
        raise ImportError(
            "python-docx manquant. Installer : pip install python-docx"
        ) from exc

    doc = Document(file_path)
    paragraphs = [para.text for para in doc.paragraphs if para.text.strip()]
    logger.debug("DOCX parsé : %s (%d paragraphes)", file_path, len(paragraphs))
    return "\n".join(paragraphs)


def parse_resume_file(file_path: str, mime_type: str) -> str:
    """Point d'entrée principal du parser.

    Args:
        file_path: Chemin absolu vers le fichier sur disque.
        mime_type:  MIME type détecté lors de l'upload.

    Returns:
        Texte brut nettoyé, prêt pour le module NLP.

    Raises:
        ValueError: Si le mime_type n'est pas supporté.
        FileNotFoundError: Si le fichier est introuvable.
        RuntimeError: Si l'extraction échoue.
    """
    if not Path(file_path).exists():
        raise FileNotFoundError(f"Fichier introuvable : {file_path}")

    mime_type = mime_type.strip().lower()

    try:
        if mime_type == MIME_PDF:
            raw = _extract_text_from_pdf(file_path)
        elif mime_type == MIME_DOCX:
            raw = _extract_text_from_docx(file_path)
        else:
            raise ValueError(
                f"Format non supporté : {mime_type}. "
                f"Formats acceptés : PDF, DOCX."
            )
    except (ValueError, FileNotFoundError):
        raise
    except Exception as exc:
        logger.exception("Erreur lors du parsing de %s", file_path)
        raise RuntimeError(f"Échec de l'extraction du texte : {exc}") from exc

    cleaned = _clean_text(raw)
    logger.info(
        "Texte extrait depuis %s — %d caractères après nettoyage",
        Path(file_path).name,
        len(cleaned),
    )
    return cleaned