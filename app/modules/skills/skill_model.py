# app/modules/skills/skill_model.py

from datetime import datetime

from sqlalchemy import Boolean, Column, DateTime, Enum as SAEnum, Integer, String, Text

from app.database import Base
from app.shared.enums import SkillCategory, SkillType


class Skill(Base):
    """
    Table 'skills' — Référentiel central des compétences.

    Propriétaire  : Membre 2
    Consommateurs : Module NLP (Membre 1), Matching, Skill Gap, Jobs (Membre 2)

    Colonnes clés
    -------------
    skill_type      : hard | soft  (enum SkillType)
    sub_category    : sous-domaine technique (enum SkillCategory) — optionnel
    normalized_name : version lowercase/nettoyée utilisée par le NLP et le Matching
    """

    __tablename__ = "skills"

    # ── Clé primaire ───────────────────────────────────────────────────────────
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)

    # ── Identification ─────────────────────────────────────────────────────────
    name = Column(
        String(100),
        unique=True,
        nullable=False,
        index=True,
        comment="Nom affiché de la compétence (ex: Python, Communication)",
    )
    normalized_name = Column(
        String(100),
        unique=True,
        nullable=False,
        index=True,
        comment="Nom normalisé lowercase sans ponctuation — clé de matching NLP",
    )

    # ── Classification ─────────────────────────────────────────────────────────
    skill_type = Column(
        SAEnum(SkillType, values_callable=lambda e: [i.value for i in e]),
        nullable=False,
        comment="hard (technique) ou soft (comportementale)",
    )
    sub_category = Column(
        SAEnum(SkillCategory, values_callable=lambda e: [i.value for i in e]),
        nullable=True,
        comment="Sous-domaine optionnel : programming, ai_ml, database, devops…",
    )

    # ── Description ────────────────────────────────────────────────────────────
    description = Column(
        Text,
        nullable=True,
        comment="Description libre de la compétence",
    )

    # ── Statut ─────────────────────────────────────────────────────────────────
    is_active = Column(
        Boolean,
        default=True,
        nullable=False,
        comment="False = désactivée, non suggérée dans l'UI ni utilisée par le NLP",
    )

    # ── Timestamps ─────────────────────────────────────────────────────────────
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(
        DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        nullable=False,
    )

    def __repr__(self) -> str:
        return (
            f"<Skill id={self.id} name='{self.name}' "
            f"type='{self.skill_type}' active={self.is_active}>"
        )