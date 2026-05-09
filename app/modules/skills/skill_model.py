"""
skills/skill_model.py — Skill SQLAlchemy model.

The skills table is the reference taxonomy of competences.
It is populated via:
  - scripts/seed_skills.py  (initial load from CSV)
  - POST /skills            (admin endpoint)
  - NLP module              (auto-discovery at extraction time)

Relationships (defined in other modules):
  Skill ──(M:N)── Job      (via job_skills association table — Phase Membre 2)
  Skill ──(M:N)── Profile  (via profile_skills — Phase 3)
"""

from datetime import datetime, timezone

from sqlalchemy import DateTime, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


def _now() -> datetime:
    return datetime.now(timezone.utc)


class Skill(Base):
    __tablename__ = "skills"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)

    name: Mapped[str] = mapped_column(
        String(100),
        unique=True,
        index=True,
        nullable=False,
        doc="Canonical skill name in lowercase-normalised form. E.g. 'python', 'react'.",
    )

    # Human-readable display name (may differ in casing from `name`)
    display_name: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        doc="Display-friendly version. E.g. 'Python', 'React', 'Power BI'.",
    )

    # Category — matches SkillCategory enum
    category: Mapped[str | None] = mapped_column(
        String(50),
        nullable=True,
        index=True,
        doc="Skill sub-domain. E.g. 'ai_ml', 'web_frontend'. See shared/enums.py SkillCategory.",
    )

    # Skill type: 'hard' or 'soft'
    skill_type: Mapped[str] = mapped_column(
        String(10),
        nullable=False,
        default="hard",
        doc="'hard' (technical) or 'soft' (interpersonal). See shared/enums.py SkillType.",
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=_now,
        nullable=False,
    )

    def __repr__(self) -> str:
        return f"<Skill id={self.id} name={self.name!r} type={self.skill_type}>"
