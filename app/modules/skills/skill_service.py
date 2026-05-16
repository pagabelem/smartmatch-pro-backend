# app/modules/skills/skill_service.py

from typing import List, Optional

from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.core.exceptions import ConflictException, NotFoundException
from app.modules.skills.skill_model import Skill
from app.modules.skills.skill_schema import SkillCreate, SkillUpdate
from app.shared.pagination import PaginationParams, paginate_query
from app.shared.utils import normalize_skill


class SkillService:
    """
    CRUD complet pour le référentiel de compétences.

    Convention NotFoundException : NotFoundException("Skill", id)
    Convention ConflictException  : ConflictException("message explicite")
    """

    # ── CREATE ─────────────────────────────────────────────────────────────────
    @staticmethod
    def create(db: Session, data: SkillCreate) -> Skill:
        """
        Crée une nouvelle compétence.
        Lève ConflictException si le nom normalisé existe déjà.
        """
        normalized = normalize_skill(data.name)

        existing = db.query(Skill).filter(
            Skill.normalized_name == normalized
        ).first()
        if existing:
            raise ConflictException(
                f"La compétence '{data.name}' existe déjà "
                f"(nom normalisé : '{normalized}')."
            )

        skill = Skill(
            name=data.name,
            normalized_name=normalized,
            skill_type=data.skill_type.value,
            sub_category=data.sub_category.value if data.sub_category else None,
            description=data.description,
            is_active=True,
        )
        db.add(skill)
        db.commit()
        db.refresh(skill)
        return skill

    # ── READ BY ID ─────────────────────────────────────────────────────────────
    @staticmethod
    def get_by_id(db: Session, skill_id: int) -> Skill:
        """Lève NotFoundException si la compétence n'existe pas."""
        skill = db.query(Skill).filter(Skill.id == skill_id).first()
        if not skill:
            raise NotFoundException("Skill", skill_id)
        return skill

    # ── READ BY NAME ───────────────────────────────────────────────────────────
    @staticmethod
    def get_by_name(db: Session, name: str) -> Optional[Skill]:
        """Recherche par nom normalisé. Retourne None si absent."""
        return db.query(Skill).filter(
            Skill.normalized_name == normalize_skill(name)
        ).first()

    # ── READ ALL (paginé) ──────────────────────────────────────────────────────
    @staticmethod
    def get_all(
        db: Session,
        params: PaginationParams,
        skill_type: Optional[str] = None,
        sub_category: Optional[str] = None,
        is_active: Optional[bool] = True,
        search: Optional[str] = None,
    ) -> dict:
        """
        Liste paginée avec filtres optionnels.
        Utilise paginate_query() de shared/pagination.py.
        """
        query = db.query(Skill)

        if skill_type:
            query = query.filter(Skill.skill_type == skill_type)
        if sub_category:
            query = query.filter(Skill.sub_category == sub_category)
        if is_active is not None:
            query = query.filter(Skill.is_active == is_active)
        if search:
            term = f"%{normalize_skill(search)}%"
            query = query.filter(
                or_(
                    Skill.normalized_name.ilike(term),
                    Skill.description.ilike(term),
                )
            )

        query = query.order_by(Skill.normalized_name.asc())
        return paginate_query(query, params)

    # ── UPDATE ─────────────────────────────────────────────────────────────────
    @staticmethod
    def update(db: Session, skill_id: int, data: SkillUpdate) -> Skill:
        """
        Mise à jour partielle.
        Vérifie l'unicité du nouveau nom si le champ name est modifié.
        """
        skill = SkillService.get_by_id(db, skill_id)
        update_data = data.model_dump(exclude_unset=True)

        if "name" in update_data:
            new_normalized = normalize_skill(update_data["name"])
            conflict = db.query(Skill).filter(
                Skill.normalized_name == new_normalized,
                Skill.id != skill_id,
            ).first()
            if conflict:
                raise ConflictException(
                    f"Le nom '{update_data['name']}' est déjà utilisé par "
                    f"une autre compétence (id={conflict.id})."
                )
            update_data["normalized_name"] = new_normalized

        # Convertir les enums en leur valeur string pour SQLAlchemy
        if "skill_type" in update_data and hasattr(update_data["skill_type"], "value"):
            update_data["skill_type"] = update_data["skill_type"].value
        if "sub_category" in update_data and update_data["sub_category"] is not None:
            if hasattr(update_data["sub_category"], "value"):
                update_data["sub_category"] = update_data["sub_category"].value

        for field, value in update_data.items():
            setattr(skill, field, value)

        db.commit()
        db.refresh(skill)
        return skill

    # ── DELETE ─────────────────────────────────────────────────────────────────
    @staticmethod
    def delete(db: Session, skill_id: int) -> dict:
        """Suppression définitive. Lève NotFoundException si absent."""
        skill = SkillService.get_by_id(db, skill_id)
        name = skill.name
        db.delete(skill)
        db.commit()
        return {"message": f"Compétence '{name}' supprimée avec succès."}

    # ── NAMES LIST (pour NLP et Matching) ──────────────────────────────────────
    @staticmethod
    def get_names_list(
        db: Session,
        skill_type: Optional[str] = None,
    ) -> dict:
        """
        Retourne les noms normalisés de toutes les compétences actives.
        Utilisé par :
          - Le NLP du Membre 1  (skill_extractor.py)
          - Le Matching du Membre 2 (cosine_matcher.py)

        Paramètre skill_type optionnel pour ne récupérer que 'hard' ou 'soft'.
        """
        query = db.query(Skill.normalized_name).filter(Skill.is_active == True)
        if skill_type:
            query = query.filter(Skill.skill_type == skill_type)
        results = query.order_by(Skill.normalized_name.asc()).all()
        names = [r.normalized_name for r in results]
        return {"total": len(names), "names": names}