# app/modules/favorites/favorite_model.py

from datetime import datetime

from sqlalchemy import Column, DateTime, ForeignKey, Integer, UniqueConstraint

from app.database import Base


class Favorite(Base):
    """
    Table 'favorites' — Offres mises en favoris par un utilisateur.
    Propriétaire  : Membre 2
    Consommateurs : Dashboard, Frontend Favorites page
    """

    __tablename__ = "favorites"

    # ── Clé primaire ───────────────────────────────────────────────────────────
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)

    # ── Clés étrangères ────────────────────────────────────────────────────────
    user_id = Column(
        Integer,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="Utilisateur qui a mis l'offre en favori"
    )
    job_id = Column(
        Integer,
        ForeignKey("jobs.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="Offre d'emploi mise en favori"
    )

    # ── Timestamp ──────────────────────────────────────────────────────────────
    created_at = Column(
        DateTime,
        default=datetime.utcnow,
        nullable=False,
        comment="Date d'ajout en favori"
    )

    # ── Contrainte d'unicité ───────────────────────────────────────────────────
    __table_args__ = (
        UniqueConstraint("user_id", "job_id", name="uq_favorite_user_job"),
    )

    def __repr__(self) -> str:
        return f"<Favorite id={self.id} user_id={self.user_id} job_id={self.job_id}>"