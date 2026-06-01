# app/modules/skill_gap/skill_gap_model.py

from datetime import datetime, timezone
from sqlalchemy import DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.types import JSON
from app.database import Base


def _now() -> datetime:
    return datetime.now(timezone.utc)


class SkillGap(Base):
    """
    Table 'skill_gaps' — Analyse des compétences manquantes.
    Compare les skills d'un profil avec celles requises par une offre.
    """
    __tablename__ = "skill_gaps"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)

    user_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    job_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("jobs.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Compétences que le profil possède ET que le job requiert
    matching_skills: Mapped[list] = mapped_column(
        JSON,
        nullable=False,
        default=list,
        doc="Skills en commun entre le profil et l'offre.",
    )

    # Compétences requises par le job mais absentes du profil
    missing_skills: Mapped[list] = mapped_column(
        JSON,
        nullable=False,
        default=list,
        doc="Skills requises par l'offre mais absentes du profil.",
    )

    # Compétences du profil non requises par le job
    extra_skills: Mapped[list] = mapped_column(
        JSON,
        nullable=False,
        default=list,
        doc="Skills du profil non requises par l'offre.",
    )

    # Pourcentage de couverture (0-100)
    coverage_percent: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        doc="Pourcentage des skills requises que le profil couvre.",
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=_now,
        nullable=False,
    )

    def __repr__(self) -> str:
        return (
            f"<SkillGap user={self.user_id} job={self.job_id} "
            f"coverage={self.coverage_percent}%>"
        )