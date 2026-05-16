"""
shared/validators.py — Reusable Pydantic v2 field validators and value checkers.

These are pure functions / annotated types that can be used in any Pydantic schema
across the project.

Usage
-----
  from app.shared.validators import validate_password_strength, NonEmptyStr

  class RegisterSchema(BaseModel):
      email:    EmailStr
      password: str

      @field_validator("password")
      @classmethod
      def password_strength(cls, v: str) -> str:
          return validate_password_strength(v)
"""

import re
from typing import Annotated

from pydantic import Field, StringConstraints

from app.core.constants import PASSWORD_MAX_LENGTH, PASSWORD_MIN_LENGTH


# ── Annotated string types (drop-in replacements for `str` in schemas) ────────
NonEmptyStr = Annotated[
    str,
    StringConstraints(strip_whitespace=True, min_length=1),
]
"""A non-empty, whitespace-stripped string."""

ShortStr = Annotated[
    str,
    StringConstraints(strip_whitespace=True, min_length=1, max_length=255),
]
"""A non-empty string capped at 255 characters — suitable for names, titles."""

LongStr = Annotated[
    str,
    StringConstraints(strip_whitespace=True, min_length=1, max_length=5000),
]
"""A non-empty string up to 5 000 characters — suitable for descriptions."""


# ── Password validator ────────────────────────────────────────────────────────
def validate_password_strength(password: str) -> str:
    """
    Enforce password strength rules.

    Rules:
      - At least PASSWORD_MIN_LENGTH characters (default: 8).
      - At most PASSWORD_MAX_LENGTH characters (default: 128).
      - At least one uppercase letter.
      - At least one lowercase letter.
      - At least one digit.

    Returns the password unchanged if valid.
    Raises ValueError (caught by Pydantic) if invalid.

    Example:
        validate_password_strength("Secure1!")  → "Secure1!"
        validate_password_strength("weak")      → raises ValueError
    """
    if len(password) < PASSWORD_MIN_LENGTH:
        raise ValueError(
            f"Password must be at least {PASSWORD_MIN_LENGTH} characters long."
        )
    if len(password) > PASSWORD_MAX_LENGTH:
        raise ValueError(
            f"Password must not exceed {PASSWORD_MAX_LENGTH} characters."
        )
    if not re.search(r"[A-Z]", password):
        raise ValueError("Password must contain at least one uppercase letter.")
    if not re.search(r"[a-z]", password):
        raise ValueError("Password must contain at least one lowercase letter.")
    if not re.search(r"\d", password):
        raise ValueError("Password must contain at least one digit.")
    return password


# ── Email validator ───────────────────────────────────────────────────────────
def validate_email_format(email: str) -> str:
    """
    Basic email format check beyond what Pydantic's EmailStr provides.
    Rejects obviously disposable/test domains if needed.

    Returns the lowercased, stripped email on success.
    """
    email = email.strip().lower()
    pattern = r"^[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}$"
    if not re.match(pattern, email):
        raise ValueError(f"'{email}' is not a valid email address.")
    return email


# ── Phone number validator ────────────────────────────────────────────────────
def validate_phone(phone: str) -> str:
    """
    Accept international phone numbers in E.164 format (+212XXXXXXXXX)
    or local formats (0XXXXXXXXX).

    Strips spaces and dashes before checking.

    Examples:
        validate_phone("+212 6 12 34 56 78")  → "+212612345678"
        validate_phone("06-12-34-56-78")       → "0612345678"
    """
    cleaned = re.sub(r"[\s\-\.]", "", phone)
    if not re.match(r"^(\+?\d{7,15})$", cleaned):
        raise ValueError(
            f"'{phone}' is not a valid phone number. "
            "Use E.164 format: +212612345678"
        )
    return cleaned


# ── URL validator ─────────────────────────────────────────────────────────────
def validate_url(url: str) -> str:
    """
    Ensure a URL starts with http:// or https://.

    Example:
        validate_url("https://linkedin.com/in/alice")  → same
        validate_url("linkedin.com/in/alice")          → raises ValueError
    """
    url = url.strip()
    if not re.match(r"^https?://", url, re.IGNORECASE):
        raise ValueError(
            f"'{url}' is not a valid URL. Must start with http:// or https://"
        )
    return url


# ── Skill list validator ──────────────────────────────────────────────────────
def validate_skills_list(skills: list[str]) -> list[str]:
    """
    Validate and normalize a list of skill strings.

    Rules:
      - List must contain at least 1 item.
      - Each skill must be a non-empty string of 1–100 characters.
      - Duplicates (case-insensitive) are removed.

    Returns a deduplicated, stripped list.

    Example:
        validate_skills_list(["Python", "  sql ", "Python"])
        → ["Python", "sql"]
    """
    if not skills:
        raise ValueError("At least one skill must be provided.")

    cleaned: list[str] = []
    seen: set[str] = set()

    for skill in skills:
        if not isinstance(skill, str):
            raise ValueError(f"Each skill must be a string, got: {type(skill).__name__}")
        skill = skill.strip()
        if not skill:
            continue
        if len(skill) > 100:
            raise ValueError(
                f"Skill '{skill[:20]}…' exceeds the maximum length of 100 characters."
            )
        key = skill.lower()
        if key not in seen:
            seen.add(key)
            cleaned.append(skill)

    if not cleaned:
        raise ValueError("Skills list cannot be empty after cleaning.")

    return cleaned


# ── Pagination validator ──────────────────────────────────────────────────────
def validate_page(page: int) -> int:
    """Ensure page number is a positive integer."""
    if page < 1:
        raise ValueError("Page number must be >= 1.")
    return page


def validate_page_size(page_size: int, max_size: int = 100) -> int:
    """Ensure page_size is within [1, max_size]."""
    if page_size < 1:
        raise ValueError("Page size must be >= 1.")
    if page_size > max_size:
        raise ValueError(f"Page size must be <= {max_size}.")
    return page_size


# ── Score validator ───────────────────────────────────────────────────────────
def validate_match_score(score: float) -> float:
    """Ensure a match score is within [0.0, 100.0]."""
    if not (0.0 <= score <= 100.0):
        raise ValueError(f"Match score must be between 0 and 100, got {score}.")
    return round(score, 2)