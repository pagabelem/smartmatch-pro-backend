"""
auth/auth_model.py — RefreshToken model.

Relationships
-------------
    User  ──(1:N)──  RefreshToken
"""

from datetime import datetime, timezone
from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.modules.users.user_model import User

# En haut du fichier auth_model.py
from typing import TYPE_CHECKING


from app.modules.users.user_model import User



def _now() -> datetime:
    return datetime.now(timezone.utc)


class RefreshToken(Base):
    """
    RefreshToken model to manage server-side session invalidation.
    """
    __tablename__ = "refresh_tokens"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)

    # The actual token string
    token: Mapped[str] = mapped_column(
        Text,
        unique=True,
        nullable=False,
        index=True,
        doc="The raw refresh token string. Index for fast lookup on each refresh.",
    )

    # Foreign key to User
    user_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Lifecycle
    is_revoked: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
        doc="Set to True on logout or when a newer token is issued.",
    )

    expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        doc="Token expiry — checked on every refresh request.",
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=_now,
        nullable=False,
    )

    # Device / session context
    user_agent: Mapped[str | None] = mapped_column(String(500), nullable=True)
    ip_address: Mapped[str | None] = mapped_column(String(50), nullable=True)

    # Relationship - Utilisation de la classe User importée
    user: Mapped["User"] = relationship("User", back_populates="refresh_tokens")

    def __repr__(self) -> str:
        return (
            f"<RefreshToken id={self.id} user_id={self.user_id} "
            f"revoked={self.is_revoked}>"
        )