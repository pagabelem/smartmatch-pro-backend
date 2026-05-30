"""
tests/test_resumes.py
Suite de tests pytest pour le module Resumes (Phase 4).

Prérequis :
  - tests/conftest.py doit fournir : test_client, test_db, test_user_token, test_profile
  - SQLite en mémoire pour les tests (override de get_db)
  - Fichiers de test dans tests/fixtures/
"""

import io
import os
import math
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest
from httpx import AsyncClient


# ============================================================
# Fixtures locales
# ============================================================

VALID_PDF_CONTENT = b"%PDF-1.4 fake pdf content for testing"
VALID_DOCX_CONTENT = b"PK fake docx content for testing"  # DOCX = ZIP

FIXTURES_DIR = Path(__file__).parent / "fixtures"


def make_upload_file(filename: str, content: bytes, content_type: str):
    """Helper pour créer un fichier multipart pour httpx."""
    return ("file", (filename, io.BytesIO(content), content_type))


# ============================================================
# Tests : Upload
# ============================================================

@pytest.mark.asyncio
async def test_upload_pdf_success(async_client: AsyncClient, auth_headers: dict):
    """Un PDF valide doit être uploadé avec succès (201)."""
    files = [make_upload_file("cv_test.pdf", VALID_PDF_CONTENT, "application/pdf")]

    with patch("app.modules.resumes.resume_service.extract_raw_text", return_value="Extracted text"):
        response = await async_client.post(
            "/api/v1/resumes/upload",
            headers=auth_headers,
            files=files,
        )

    assert response.status_code == 201
    data = response.json()["data"]
    assert data["filename"] == "cv_test.pdf"
    assert data["is_parsed"] is True
    assert "id" in data


@pytest.mark.asyncio
async def test_upload_docx_success(async_client: AsyncClient, auth_headers: dict):
    """Un DOCX valide doit être uploadé avec succès (201)."""
    files = [make_upload_file(
        "cv_test.docx",
        VALID_DOCX_CONTENT,
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    )]

    with patch("app.modules.resumes.resume_service.extract_raw_text", return_value="Resume text"):
        response = await async_client.post(
            "/api/v1/resumes/upload",
            headers=auth_headers,
            files=files,
        )

    assert response.status_code == 201
    assert response.json()["data"]["is_parsed"] is True


@pytest.mark.asyncio
async def test_upload_invalid_extension(async_client: AsyncClient, auth_headers: dict):
    """Un fichier avec extension non autorisée doit être rejeté (400/422)."""
    files = [make_upload_file("cv.txt", b"hello", "text/plain")]

    response = await async_client.post(
        "/api/v1/resumes/upload",
        headers=auth_headers,
        files=files,
    )

    assert response.status_code in (400, 422)
    body = response.json()
    assert "extension" in str(body).lower() or "non autorisée" in str(body).lower()


@pytest.mark.asyncio
async def test_upload_too_large(async_client: AsyncClient, auth_headers: dict, settings_override):
    """Un fichier dépassant MAX_FILE_SIZE doit être rejeté."""
    # Simuler un fichier de 11 Mo avec MAX=10 Mo
    big_content = b"0" * (11 * 1024 * 1024)
    files = [make_upload_file("big_cv.pdf", big_content, "application/pdf")]

    response = await async_client.post(
        "/api/v1/resumes/upload",
        headers=auth_headers,
        files=files,
    )

    assert response.status_code in (400, 413, 422)


@pytest.mark.asyncio
async def test_upload_unauthenticated(async_client: AsyncClient):
    """L'upload sans token doit retourner 401."""
    files = [make_upload_file("cv.pdf", VALID_PDF_CONTENT, "application/pdf")]
    response = await async_client.post("/api/v1/resumes/upload", files=files)
    assert response.status_code == 401


# ============================================================
# Tests : Extraction de texte
# ============================================================

def test_extract_text_from_pdf(tmp_path):
    """L'extraction PDF doit retourner une chaîne non vide sur un vrai PDF minimal."""
    from app.modules.resumes.file_parser import parse_resume_file

    # Créer un PDF minimal valide avec pypdf
    try:
        import pypdf
        from pypdf import PdfWriter

        pdf_path = tmp_path / "test.pdf"
        writer = PdfWriter()
        writer.add_blank_page(width=200, height=200)
        with open(pdf_path, "wb") as f:
            writer.write(f)

        result = parse_resume_file(str(pdf_path), "application/pdf")
        assert isinstance(result, str)  # Peut être vide pour un PDF sans texte
    except ImportError:
        pytest.skip("pypdf non installé")


def test_extract_text_from_docx(tmp_path):
    """L'extraction DOCX doit retourner le texte des paragraphes."""
    from app.modules.resumes.file_parser import parse_resume_file

    try:
        from docx import Document

        doc = Document()
        doc.add_paragraph("Python Developer")
        doc.add_paragraph("FastAPI · SQLAlchemy · React")
        docx_path = tmp_path / "test.docx"
        doc.save(str(docx_path))

        mime = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        result = parse_resume_file(str(docx_path), mime)

        assert "Python Developer" in result
        assert "FastAPI" in result
    except ImportError:
        pytest.skip("python-docx non installé")


def test_extract_text_unsupported_format(tmp_path):
    """Un mime_type non supporté doit lever ValueError."""
    from app.modules.resumes.file_parser import parse_resume_file

    txt_path = tmp_path / "cv.txt"
    txt_path.write_text("hello")

    with pytest.raises(ValueError, match="non supporté"):
        parse_resume_file(str(txt_path), "text/plain")


def test_extract_text_file_not_found():
    """Un chemin inexistant doit lever FileNotFoundError."""
    from app.modules.resumes.file_parser import parse_resume_file

    with pytest.raises(FileNotFoundError):
        parse_resume_file("/nonexistent/path/cv.pdf", "application/pdf")


# ============================================================
# Tests : CRUD
# ============================================================

@pytest.mark.asyncio
async def test_get_resume_by_id(async_client: AsyncClient, auth_headers: dict, seeded_resume):
    """GET /resumes/{id} doit retourner les données du CV."""
    resume_id = seeded_resume["id"]
    response = await async_client.get(f"/api/v1/resumes/{resume_id}", headers=auth_headers)

    assert response.status_code == 200
    data = response.json()["data"]
    assert data["id"] == resume_id
    assert "filename" in data
    assert "file_path" in data


@pytest.mark.asyncio
async def test_get_resume_not_found(async_client: AsyncClient, auth_headers: dict):
    """GET /resumes/99999 doit retourner 404."""
    response = await async_client.get("/api/v1/resumes/99999", headers=auth_headers)
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_get_resume_text(async_client: AsyncClient, auth_headers: dict, seeded_resume):
    """GET /resumes/{id}/text doit retourner le raw_text."""
    resume_id = seeded_resume["id"]
    response = await async_client.get(f"/api/v1/resumes/{resume_id}/text", headers=auth_headers)

    assert response.status_code == 200
    data = response.json()["data"]
    assert "raw_text" in data
    assert "is_parsed" in data


@pytest.mark.asyncio
async def test_get_resumes_by_profile(async_client: AsyncClient, auth_headers: dict, test_profile, seeded_resume):
    """GET /resumes/profile/{id} doit retourner la liste paginée."""
    profile_id = test_profile["id"]
    response = await async_client.get(
        f"/api/v1/resumes/profile/{profile_id}",
        headers=auth_headers,
    )

    assert response.status_code == 200
    data = response.json()["data"]
    assert "items" in data
    assert "total" in data
    assert "pages" in data
    assert data["total"] >= 1


@pytest.mark.asyncio
async def test_delete_resume(async_client: AsyncClient, auth_headers: dict, seeded_resume, tmp_path):
    """DELETE /resumes/{id} doit supprimer fichier + BDD."""
    resume_id = seeded_resume["id"]

    # Crée le fichier physique fictif pour que le service trouve quelque chose à supprimer
    with patch("app.modules.resumes.resume_service.os.remove") as mock_remove, \
         patch("pathlib.Path.exists", return_value=True):

        response = await async_client.delete(
            f"/api/v1/resumes/{resume_id}",
            headers=auth_headers,
        )

    assert response.status_code == 200

    # Vérifie que le CV n'existe plus en BDD
    get_response = await async_client.get(
        f"/api/v1/resumes/{resume_id}",
        headers=auth_headers,
    )
    assert get_response.status_code == 404


@pytest.mark.asyncio
async def test_delete_resume_forbidden(async_client: AsyncClient, other_user_headers: dict, seeded_resume):
    """Un utilisateur ne doit pas pouvoir supprimer le CV d'un autre."""
    resume_id = seeded_resume["id"]
    response = await async_client.delete(
        f"/api/v1/resumes/{resume_id}",
        headers=other_user_headers,
    )
    assert response.status_code == 403


# ============================================================
# Tests : Service unitaires
# ============================================================

@pytest.mark.asyncio
async def test_service_validate_extension(tmp_path):
    """Le service doit rejeter une extension non autorisée."""
    from app.modules.resumes.resume_service import _validate_file
    from app.core.exceptions import ValidationException

    with pytest.raises(ValidationException, match="extension"):
        _validate_file("cv.exe", 100)


@pytest.mark.asyncio
async def test_service_validate_size(tmp_path):
    """Le service doit rejeter un fichier trop grand."""
    from app.modules.resumes.resume_service import _validate_file
    from app.core.exceptions import ValidationException
    from app.config import settings

    oversized = settings.max_file_size_bytes + 1
    with pytest.raises(ValidationException, match="volumineux"):
        _validate_file("cv.pdf", oversized)