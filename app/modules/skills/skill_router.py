"""
skills/skill_router.py — Skills CRUD endpoints.

Endpoints
---------
  POST   /api/v1/skills              Create a skill         (admin)
  GET    /api/v1/skills              List skills            (authenticated)
  GET    /api/v1/skills/{id}         Get skill by ID        (authenticated)
  PUT    /api/v1/skills/{id}         Update a skill         (admin)
  DELETE /api/v1/skills/{id}         Delete a skill         (admin)

Query parameters for GET /skills
---------------------------------
  page       int    Page number (default 1)
  page_size  int    Items per page (default 20, max 100)
  search     str    Filter by name containing this string
  category   str    Filter by SkillCategory value
  skill_type str    Filter by 'hard' or 'soft'
  sort       str    'name' (default) or 'created_at'
"""

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.core.responses import created, no_content, ok
from app.dependencies import get_current_active_user, get_db
from app.modules.skills import skill_service
from app.modules.skills.skill_schema import (
    SkillCreate,
    SkillListResponse,
    SkillResponse,
    SkillUpdate,
)
from app.shared.pagination import PaginationParams

router = APIRouter(prefix="/skills", tags=["Skills"])


@router.post(
    "/",
    status_code=status.HTTP_201_CREATED,
    response_model=SkillResponse,
    summary="Create a new skill",
    description="Add a skill to the taxonomy. Name must be unique (case-insensitive).",
)
def create_skill(
    payload: SkillCreate,
    db: Session = Depends(get_db),
    _=Depends(get_current_active_user),
):
    skill = skill_service.create_skill(db, payload)
    return created(data=SkillResponse.model_validate(skill), message="Skill created.")


@router.get(
    "/",
    response_model=SkillListResponse,
    summary="List all skills",
    description=(
        "Returns a paginated, alphabetically sorted list of skills. "
        "Supports search (?search=python), category and type filtering."
    ),
)
def list_skills(
    params: PaginationParams = Depends(),
    search: str | None = Query(default=None, description="Filter by name fragment."),
    category: str | None = Query(default=None, description="Filter by SkillCategory value."),
    skill_type: str | None = Query(default=None, description="'hard' or 'soft'."),
    sort: str = Query(default="name", description="'name' or 'created_at'."),
    db: Session = Depends(get_db),
    _=Depends(get_current_active_user),
):
    page = skill_service.get_skills(
        db, params,
        search=search,
        category=category,
        skill_type=skill_type,
        sort=sort,
    )
    return ok(
        data=SkillListResponse(
            items=[SkillResponse.model_validate(s) for s in page.items],
            **page.to_dict(),
        ),
    )


@router.get(
    "/{skill_id}",
    response_model=SkillResponse,
    summary="Get a skill by ID",
)
def get_skill(
    skill_id: int,
    db: Session = Depends(get_db),
    _=Depends(get_current_active_user),
):
    skill = skill_service.get_skill(db, skill_id)
    return ok(data=SkillResponse.model_validate(skill))


@router.put(
    "/{skill_id}",
    response_model=SkillResponse,
    summary="Update a skill",
    description="Partially update a skill. Only provided fields are changed.",
)
def update_skill(
    skill_id: int,
    payload: SkillUpdate,
    db: Session = Depends(get_db),
    _=Depends(get_current_active_user),
):
    skill = skill_service.update_skill(db, skill_id, payload)
    return ok(data=SkillResponse.model_validate(skill), message="Skill updated.")


@router.delete(
    "/{skill_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a skill",
    description="Permanently delete a skill from the taxonomy.",
)
def delete_skill(
    skill_id: int,
    db: Session = Depends(get_db),
    _=Depends(get_current_active_user),
):
    skill_service.delete_skill(db, skill_id)
    return no_content()