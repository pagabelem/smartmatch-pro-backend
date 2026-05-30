"""
skills/skill_service.py — Skills business logic.

Pure DB operations — no HTTP, no Request/Response objects.
All errors are raised as AppException subclasses.

Functions
---------
  create_skill(db, payload)           → Skill
  get_skill(db, skill_id)             → Skill
  get_skill_by_name(db, name)         → Skill | None
  get_skills(db, page, page_size, search, category, skill_type, sort)  → Page[Skill]
  update_skill(db, skill_id, payload) → Skill
  delete_skill(db, skill_id)          → None
  bulk_upsert(db, names)              → list[Skill]
"""

from sqlalchemy import asc, func
from sqlalchemy.orm import Session

from app.core.exceptions import ConflictException, NotFoundException
from app.modules.skills.skill_model import Skill
from app.modules.skills.skill_schema import SkillCreate, SkillUpdate
from app.shared.pagination import Page, PaginationParams, paginate_query
from app.shared.utils import normalize_skill


def create_skill(db: Session, payload: SkillCreate) -> Skill:
    """
    Create a new skill.

    Raises:
      ConflictException — if a skill with the same normalised name already exists.
    """
    existing = db.query(Skill).filter(Skill.name == payload.name).first()
    if existing:
        raise ConflictException(f"Skill '{payload.name}' already exists.")

    skill = Skill(
        name=payload.name,
        display_name=payload.display_name or payload.name.title(),
        category=payload.category.value if payload.category else None,
        skill_type=payload.skill_type.value,
    )
    db.add(skill)
    db.commit()
    db.refresh(skill)
    return skill


def get_skill(db: Session, skill_id: int) -> Skill:
    """
    Retrieve a skill by ID.

    Raises:
      NotFoundException — if the skill does not exist.
    """
    skill = db.get(Skill, skill_id)
    if not skill:
        raise NotFoundException("Skill", skill_id)
    return skill


def get_skill_by_name(db: Session, name: str) -> Skill | None:
    """Return a skill by normalised name, or None if not found."""
    return db.query(Skill).filter(Skill.name == normalize_skill(name)).first()


def get_skills(
    db: Session,
    params: PaginationParams,
    search: str | None = None,
    category: str | None = None,
    skill_type: str | None = None,
    sort: str = "name",          # "name" | "created_at"
) -> Page:
    """
    List skills with optional search, filters, sorting, and pagination.

    Parameters
    ----------
    search      : filter by name containing this string (case-insensitive).
    category    : filter by SkillCategory value.
    skill_type  : filter by 'hard' or 'soft'.
    sort        : 'name' (default, alphabetical) or 'created_at' (newest first).

    Returns a Page object with items + pagination metadata.
    """
    query = db.query(Skill)

    # Filter: search
    if search:
        query = query.filter(
            Skill.name.ilike(f"%{normalize_skill(search)}%")
        )

    # Filter: category
    if category:
        query = query.filter(Skill.category == category)

    # Filter: skill_type
    if skill_type:
        query = query.filter(Skill.skill_type == skill_type)

    # Sort
    if sort == "created_at":
        query = query.order_by(Skill.created_at.desc())
    else:
        query = query.order_by(asc(func.lower(Skill.name)))   # case-insensitive alpha

    return paginate_query(query, params)


def update_skill(db: Session, skill_id: int, payload: SkillUpdate) -> Skill:
    """
    Partially update a skill.

    Only provided (non-None) fields are updated.

    Raises:
      NotFoundException  — if skill does not exist.
      ConflictException  — if the new name conflicts with another skill.
    """
    skill = get_skill(db, skill_id)

    if payload.name is not None and payload.name != skill.name:
        conflict = db.query(Skill).filter(Skill.name == payload.name).first()
        if conflict:
            raise ConflictException(f"Skill '{payload.name}' already exists.")
        skill.name = payload.name

    if payload.display_name is not None:
        skill.display_name = payload.display_name

    if payload.category is not None:
        skill.category = payload.category.value

    if payload.skill_type is not None:
        skill.skill_type = payload.skill_type.value

    db.commit()
    db.refresh(skill)
    return skill


def delete_skill(db: Session, skill_id: int) -> None:
    """
    Delete a skill by ID.

    Raises:
      NotFoundException — if skill does not exist.
    """
    skill = get_skill(db, skill_id)
    db.delete(skill)
    db.commit()


def bulk_upsert(db: Session, names: list[str]) -> list[Skill]:
    """
    Insert skills that don't exist yet, return all (existing + new).

    Used by the NLP module when it discovers skills not yet in the taxonomy.

    Example:
        skills = bulk_upsert(db, ["python", "tensorflow", "sql"])
    """
    result: list[Skill] = []
    for raw_name in names:
        normalised = normalize_skill(raw_name)
        if not normalised:
            continue
        skill = db.query(Skill).filter(Skill.name == normalised).first()
        if not skill:
            skill = Skill(
                name=normalised,
                display_name=raw_name.strip().title(),
                skill_type="hard",
            )
            db.add(skill)
        result.append(skill)

    db.commit()
    return result