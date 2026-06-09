"""
app/modules/resumes/resume_router.py
Endpoints REST pour le module Resumes.
"""

import logging
import asyncio
from pathlib import Path

from fastapi import APIRouter, Depends, UploadFile, File, Query, status, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from sqlalchemy import select

from app.config import settings
from app.core.exceptions import ForbiddenException, NotFoundException
from app.core.responses import success_response, error_response
from app.database import get_db
# ✅ Correction : On importe get_current_active_user pour bloquer les requêtes non authentifiées
from app.modules.auth.dependencies import get_current_active_user
from app.modules.users.user_model import User, Profile
from app.modules.resumes import resume_service as svc
from app.modules.resumes.resume_schema import (
    ResumeUploadResponse,
    ResumeResponse,
    ResumeListResponse,
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/resumes", tags=["Resumes"])


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _is_async(db: AsyncSession) -> bool:
    """Vérifie si la session actuelle est asynchrone."""
    return hasattr(db, "execute_with_context") or asyncio.iscoroutinefunction(db.execute)


async def _assert_owner_or_admin(
    resume_profile_id: int, 
    current_user: User | None, 
    db: AsyncSession
) -> None:
    """Vérifie que l'utilisateur est propriétaire du profil ou admin."""
    # ✅ Sécurité si la dépendance n'a pas levé d'erreur (ex: routeur mal configuré)
    if not current_user:
        raise ForbiddenException("Authentification requise pour accéder à ce CV.")
        
    stmt = select(User).where(User.id == current_user.id).options(selectinload(User.profile))
    
    if _is_async(db):
        result = await db.execute(stmt)
    else:
        result = db.execute(stmt)
        
    user_with_profile = result.scalar_one_or_none()
    
    if not user_with_profile:
        raise ForbiddenException("Utilisateur introuvable.")
        
    is_owner = (
        user_with_profile.profile is not None
        and user_with_profile.profile.id == resume_profile_id
    )
    if not (is_owner or current_user.is_superuser):
        raise ForbiddenException("Accès refusé à ce CV.")


# ---------------------------------------------------------------------------
# GET /test (route de test)
# ---------------------------------------------------------------------------

@router.get("/test", tags=["Resumes"])
async def test_resumes_route():
    """Route de test pour vérifier que le routeur est chargé."""
    return {"message": "Resumes router is working!"}


# ---------------------------------------------------------------------------
# POST /upload
# ---------------------------------------------------------------------------

@router.post(
    "/upload",
    response_model=None,
    status_code=status.HTTP_201_CREATED,
)
async def upload_resume(
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    # ✅ Correction : Dépendance stricte appliquée
    current_user: User = Depends(get_current_active_user),
):
    """Upload un CV et extrait son texte brut."""
    # ✅ Exécution adaptative (async/sync) et extraction propre du scalaire
    stmt = select(User).where(User.id == current_user.id).options(selectinload(User.profile))
    
    if _is_async(db):
        result = await db.execute(stmt)
    else:
        result = db.execute(stmt)
        
    current_user_fetched = result.scalar_one_or_none()
    
    if not current_user_fetched:
        return error_response("Utilisateur non trouvé.", code=404)
    
    if current_user_fetched.profile is None:
        return error_response("Vous devez d'abord créer un profil.", code=400)

    profile_id = current_user_fetched.profile.id

    file_path, file_size, mime_type = await svc.save_resume_file(file, profile_id)
    absolute_path = str(Path(settings.UPLOAD_DIR) / file_path)
    raw_text = svc.extract_raw_text(absolute_path, mime_type)

    resume = await svc.create_resume_record(
        db=db,
        profile_id=profile_id,
        filename=file.filename or "resume",
        file_path=file_path,
        file_size=file_size,
        mime_type=mime_type,
        raw_text=raw_text,
    )

    response_data = ResumeUploadResponse(
        id=resume.id,
        filename=resume.filename,
        file_path=resume.file_path,
        file_size=resume.file_size,
        is_parsed=resume.is_parsed,
        created_at=resume.created_at,
    ).model_dump()
    
    return success_response(data=response_data, message="CV uploadé avec succès.")


# ---------------------------------------------------------------------------
# GET /profile/{profile_id}
# ---------------------------------------------------------------------------

@router.get(
    "/profile/{profile_id}",
    response_model=None,
    summary="Liste des CVs d'un profil",
)
async def list_resumes_by_profile(
    profile_id: int,
    page: int = Query(1, ge=1),
    limit: int = Query(10, ge=1, le=50),
    db: AsyncSession = Depends(get_db),
    # ✅ Correction : Dépendance stricte appliquée
    current_user: User = Depends(get_current_active_user),
):
    """Liste paginée des CVs d'un profil."""
    # ✅ Correction : Vérifier l'existence réelle du profil pour renvoyer une 404 si manquant
    stmt_profile = select(Profile).where(Profile.id == profile_id)
    if _is_async(db):
        profile_check = await db.execute(stmt_profile)
    else:
        profile_check = db.execute(stmt_profile)
        
    if not profile_check.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Profile not found")

    await _assert_owner_or_admin(profile_id, current_user, db)

    items, total = await svc.get_resumes_by_profile(db, profile_id, page, limit)
    pages = svc.compute_pages(total, limit)

    response_data = ResumeListResponse(
        items=[ResumeResponse.model_validate(r) for r in items],
        total=total,
        page=page,
        limit=limit,
        pages=pages,
    ).model_dump()

    return success_response(data=response_data)


# ---------------------------------------------------------------------------
# GET /{resume_id}
# ---------------------------------------------------------------------------

@router.get(
    "/{resume_id}",
    response_model=None,
    summary="Récupérer un CV par ID",
)
async def get_resume(
    resume_id: int,
    db: AsyncSession = Depends(get_db),
    # ✅ Correction : Dépendance stricte appliquée
    current_user: User = Depends(get_current_active_user),
):
    """Retourne les métadonnées complètes d'un CV."""
    resume = await svc.get_resume_by_id(db, resume_id)
    await _assert_owner_or_admin(resume.profile_id, current_user, db)

    return success_response(
        data=ResumeResponse.model_validate(resume).model_dump()
    )


# ---------------------------------------------------------------------------
# GET /{resume_id}/text
# ---------------------------------------------------------------------------

@router.get(
    "/{resume_id}/text",
    response_model=None,
    summary="Texte brut extrait d'un CV",
)
async def get_resume_text(
    resume_id: int,
    db: AsyncSession = Depends(get_db),
    # ✅ Correction : Dépendance stricte appliquée
    current_user: User = Depends(get_current_active_user),
):
    """Retourne le champ `raw_text` du CV."""
    resume = await svc.get_resume_by_id(db, resume_id)
    await _assert_owner_or_admin(resume.profile_id, current_user, db)

    return success_response(
        data={
            "id": resume.id,
            "raw_text": resume.raw_text
        }
    )


# ---------------------------------------------------------------------------
# DELETE /{resume_id}
# ---------------------------------------------------------------------------

@router.delete(
    "/{resume_id}",
    status_code=status.HTTP_200_OK,
    summary="Supprimer un CV",
)
async def delete_resume(
    resume_id: int,
    db: AsyncSession = Depends(get_db),
    # ✅ Correction : Dépendance stricte appliquée
    current_user: User = Depends(get_current_active_user),
):
    """Suppression complète d'un CV (fichier + BDD)."""
    resume = await svc.get_resume_by_id(db, resume_id)
    await _assert_owner_or_admin(resume.profile_id, current_user, db)

    await svc.delete_resume(db, resume_id)
    return success_response(message=f"CV '{resume.filename}' supprimé avec succès.")