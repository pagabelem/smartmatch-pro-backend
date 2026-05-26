"""
modules/users/user_model.py — SQLAlchemy ORM models for User and Profile.

Design decisions
----------------
* User and Profile are in the same file because they are tightly coupled
  (1-to-1 relationship) and always imported together.
* Alembic will detect these models via env.py's target_metadata — make sure
  this file is imported somewhere before Alembic runs (see alembic/env.py).
* All columns have sensible defaults and server_default where appropriate.
* JSON columns (skills_extracted, etc.) use sqlalchemy's JSON type,
  which maps to TEXT on SQLite and JSONB-compatible JSON on PostgreSQL.

Relationships
-------------
  User  ──(1:1)──  Profile
  User  ──(1:N)──  RefreshToken
  User  ──(1:N)──  (Resume, Favorite, etc. — FK defined on those models)
"""

from datetime import datetime, timezone
from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.types import JSON

from app.database import Base
from typing import TYPE_CHECKING

# ── Helpers ───────────────────────────────────────────────────────────────────
def _now() -> datetime:
    """UTC-aware current datetime — used as column defaults."""
    return datetime.now(timezone.utc)


# ── User ──────────────────────────────────────────────────────────────────────
class User(Base):
    """
    Core authentication entity.

    Contains only auth-related fields. All personal data (name, bio, skills)
    lives in Profile to keep concerns separated.
    """

    __tablename__ = "users"

    # Primary key
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)

    # Authentication fields
    email: Mapped[str] = mapped_column(
        String(255),
        unique=True,
        index=True,
        nullable=False,
        doc="Unique email address used for login.",
    )
    hashed_password: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        doc="bcrypt hash — never store plain-text passwords.",
    )

    # Account state
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
        doc="Soft-disable an account without deleting it.",
    )
    is_superuser: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
        doc="Grants access to admin endpoints.",
    )

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=_now,
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=_now,
        onupdate=_now,
        nullable=False,
    )
    last_login_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        doc="Set on every successful login — useful for analytics.",
    )

    # ── Relationships ─────────────────────────────────────────────────────────
    # uselist=False → one User has exactly one Profile
    profile: Mapped["Profile"] = relationship(
        "Profile",
        back_populates="user",
        uselist=False,
        cascade="all, delete-orphan",
        lazy="select",
    )

    # One User has many RefreshTokens
    refresh_tokens: Mapped[list["RefreshToken"]] = relationship(
        "RefreshToken",
        back_populates="user",
        cascade="all, delete-orphan",
        lazy="select",
    )

    # ── Dunder ────────────────────────────────────────────────────────────────
    def __repr__(self) -> str:
        return f"<User id={self.id} email={self.email!r} active={self.is_active}>"


# ── Profile ───────────────────────────────────────────────────────────────────
class Profile(Base):
    """
    Personal and professional information about a User.

    Separated from User so that:
    1. Auth logic never touches personal data.
    2. The Matching module can read skills without loading auth fields.
    3. Profile can be extended (education, links, photo) without touching User.
    """

    __tablename__ = "profiles"

    # Primary key — same value as user_id for simplicity (1-to-1)
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)

    # Foreign key to User (1-to-1)
    user_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("users.id", ondelete="CASCADE"),
        unique=True,          # enforces the 1-to-1 at database level
        nullable=False,
        index=True,
    )

    # Personal information
    first_name: Mapped[str | None] = mapped_column(String(100), nullable=True)
    last_name: Mapped[str | None] = mapped_column(String(100), nullable=True)
    bio: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        doc="Short professional summary (displayed on profile card).",
    )
    phone: Mapped[str | None] = mapped_column(String(30), nullable=True)
    location: Mapped[str | None] = mapped_column(
        String(200),
        nullable=True,
        doc="City, Country — used to filter job recommendations.",
    )
    linkedin_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    github_url: Mapped[str | None] = mapped_column(String(500), nullable=True)

    # Education
    degree: Mapped[str | None] = mapped_column(
        String(200),
        nullable=True,
        doc="Highest degree, e.g. 'Bac+5 Master Informatique'.",
    )
    field_of_study: Mapped[str | None] = mapped_column(String(200), nullable=True)
    school: Mapped[str | None] = mapped_column(String(200), nullable=True)
    graduation_year: Mapped[int | None] = mapped_column(Integer, nullable=True)

    # Skills — manually entered by the user (raw list of strings)
    # Example: ["Python", "SQL", "Machine Learning", "communication"]
    skills_raw: Mapped[list | None] = mapped_column(
        JSON,
        nullable=True,
        default=list,
        doc="Skills entered manually by the student. JSON array of strings.",
    )

    # Skills — extracted automatically by the NLP module from CVs
    # Richer structure: {"hard_skills": [...], "soft_skills": [...]}
    skills_extracted: Mapped[dict | None] = mapped_column(
        JSON,
        nullable=True,
        default=dict,
        doc=(
            "Skills extracted by the NLP module. "
            "Structure: {hard_skills: [...], soft_skills: [...]}. "
            "Updated every time a CV is processed."
        ),
    )

    # Target job preferences (used to pre-filter recommendations)
    target_job_title: Mapped[str | None] = mapped_column(String(200), nullable=True)
    target_sectors: Mapped[list | None] = mapped_column(
        JSON,
        nullable=True,
        default=list,
        doc="List of sectors the student is interested in.",
    )
    target_contract_types: Mapped[list | None] = mapped_column(
        JSON,
        nullable=True,
        default=list,
        doc="e.g. ['CDI', 'Stage', 'Alternance']",
    )

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_now, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_now, onupdate=_now, nullable=False
    )

    # ── Relationship back to User ──────────────────────────────────────────────
    user: Mapped["User"] = relationship(
        "User",
        back_populates="profile",
    )

    # ✅ PHASE 4 — Relationship with Resume
    resumes: Mapped[list["Resume"]] = relationship(
        "Resume",
        back_populates="profile",
        cascade="all, delete-orphan",
    )

    # ── Computed helpers ──────────────────────────────────────────────────────
    @property
    def full_name(self) -> str:
        """Returns 'First Last', or email prefix if names are not set."""
        parts = filter(None, [self.first_name, self.last_name])
        return " ".join(parts) or "—"

    @property
    def all_skills(self) -> list[str]:
        """
        Merge manually-entered and NLP-extracted skills into one deduplicated list.
        Used by the Matching module.
        """
        raw: list[str] = self.skills_raw or []
        extracted: dict = self.skills_extracted or {}
        nlp_skills: list[str] = (
            extracted.get("hard_skills", []) + extracted.get("soft_skills", [])
        )
        # Lowercase + deduplicate while preserving order
        seen: set[str] = set()
        result: list[str] = []
        for skill in raw + nlp_skills:
            key = skill.lower().strip()
            if key and key not in seen:
                seen.add(key)
                result.append(skill)
        return result

    def __repr__(self) -> str:
        return (
            f"<Profile id={self.id} user_id={self.user_id} "
            f"name={self.full_name!r}>"
        )