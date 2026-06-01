# app/modules/matching/recommendation_model.py

from datetime import datetime, timezone
from sqlalchemy import DateTime, Float, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column
from app.database import Base


def _now() -> datetime:
    return datetime.now(timezone.utc)


class Recommendation(Base):
    """
    Table 'recommendations' — Résultats du matching cosinus.
    Un enregistrement = un score entre un profil et une offre d'emploi.
    """
    __tablename__ = "recommendations"

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

    score: Mapped[float] = mapped_column(
        Float,
        nullable=False,
        doc="Score cosinus entre 0.0 et 1.0",
    )

    score_label: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="Low",
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=_now,
        nullable=False,
    )

    def __repr__(self) -> str:
        return (
            f"<Recommendation user={self.user_id} "
            f"job={self.job_id} score={self.score:.2f}>"
        )