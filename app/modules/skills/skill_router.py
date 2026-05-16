# app/modules/skills/skill_router.py

from typing import Optional

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.core.responses import created, ok
from app.dependencies import get_db
from app.modules.skills.skill_schema import (
    SkillCreate,
    SkillResponse,
    SkillUpdate,
)
from app.modules.skills.skill_service import SkillService
from app.shared.pagination import PaginationParams

router = APIRouter(
    prefix="/skills",
    tags=["Skills — Référentiel de compétences"],
)


# ── POST /api/v1/skills/ ───────────────────────────────────────────────────────
@router.post(
    "/",
    status_code=status.HTTP_201_CREATED,
    summary="Créer une nouvelle compétence",
)
def create_skill(
    data: SkillCreate,
    db: Session = Depends(get_db),
):
    skill = SkillService.create(db, data)
    return created(
        data=SkillResponse.model_validate(skill).model_dump(mode="json"),
        message=f"Compétence '{skill.name}' créée avec succès.",
    )


# ── GET /api/v1/skills/ ────────────────────────────────────────────────────────
@router.get(
    "/",
    status_code=status.HTTP_200_OK,
    summary="Lister les compétences (paginé)",
)
def list_skills(
    skill_type: Optional[str] = Query(None, description="Filtrer : 'hard' ou 'soft'"),
    sub_category: Optional[str] = Query(None, description="Filtrer par sous-catégorie"),
    is_active: Optional[bool] = Query(True, description="Filtrer par statut actif"),
    search: Optional[str] = Query(None, description="Recherche par nom ou description"),
    params: PaginationParams = Depends(),
    db: Session = Depends(get_db),
):
    page = SkillService.get_all(
        db=db,
        params=params,
        skill_type=skill_type,
        sub_category=sub_category,
        is_active=is_active,
        search=search,
    )
    return ok(
        data=[SkillResponse.model_validate(s).model_dump(mode="json") for s in page.items],
        meta=page.to_dict(),
    )


# ── GET /api/v1/skills/names ───────────────────────────────────────────────────
@router.get(
    "/names",
    status_code=status.HTTP_200_OK,
    summary="Liste des noms normalisés — NLP & Matching",
)
def get_skill_names(
    skill_type: Optional[str] = Query(None, description="'hard', 'soft' ou tous"),
    db: Session = Depends(get_db),
):
    result = SkillService.get_names_list(db, skill_type=skill_type)
    return ok(data=result)


# ── GET /api/v1/skills/{skill_id} ─────────────────────────────────────────────
@router.get(
    "/{skill_id}",
    status_code=status.HTTP_200_OK,
    summary="Récupérer une compétence par son ID",
)
def get_skill(
    skill_id: int,
    db: Session = Depends(get_db),
):
    skill = SkillService.get_by_id(db, skill_id)
    return ok(data=SkillResponse.model_validate(skill).model_dump(mode="json"))


# ── PUT /api/v1/skills/{skill_id} ─────────────────────────────────────────────
@router.put(
    "/{skill_id}",
    status_code=status.HTTP_200_OK,
    summary="Mettre à jour une compétence",
)
def update_skill(
    skill_id: int,
    data: SkillUpdate,
    db: Session = Depends(get_db),
):
    skill = SkillService.update(db, skill_id, data)
    return ok(
        data=SkillResponse.model_validate(skill).model_dump(mode="json"),
        message=f"Compétence '{skill.name}' mise à jour.",
    )


# ── DELETE /api/v1/skills/{skill_id} ──────────────────────────────────────────
@router.delete(
    "/{skill_id}",
    status_code=status.HTTP_200_OK,
    summary="Supprimer une compétence",
)
def delete_skill(
    skill_id: int,
    db: Session = Depends(get_db),
):
    result = SkillService.delete(db, skill_id)
    return ok(message=result["message"])