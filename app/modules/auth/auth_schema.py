"""
auth/auth_schema.py — Pydantic v2 schemas for authentication endpoints.

Schemas defined here
---------------------
  RegisterRequest   → POST /auth/register  (input)
  LoginRequest      → POST /auth/login     (input)
  TokenResponse     → all auth endpoints   (output)
  RefreshRequest    → POST /auth/refresh   (input)
  MessageResponse   → POST /auth/logout    (output)
  UserPublic        → embedded in TokenResponse
"""

from datetime import datetime

from pydantic import BaseModel, EmailStr, Field, field_validator

from app.shared.validators import validate_password_strength


# ── Input schemas ─────────────────────────────────────────────────────────────
class RegisterRequest(BaseModel):
    """Payload for POST /auth/register."""

    email: EmailStr = Field(
        ...,
        description="Valid email address. Will be used to log in.",
        examples=["alice@example.com"],
    )
    password: str = Field(
        ...,
        min_length=8,
        max_length=128,
        description="Password (min 8 chars, 1 uppercase, 1 lowercase, 1 digit).",
    )
    first_name: str | None = Field(
        default=None,
        max_length=100,
        description="Optional first name.",
    )
    last_name: str | None = Field(
        default=None,
        max_length=100,
        description="Optional last name.",
    )

    @field_validator("password")
    @classmethod
    def password_must_be_strong(cls, v: str) -> str:
        return validate_password_strength(v)

    @field_validator("email")
    @classmethod
    def email_to_lowercase(cls, v: str) -> str:
        return v.strip().lower()


class LoginRequest(BaseModel):
    """Payload for POST /auth/login (form-compatible)."""

    email: EmailStr = Field(..., examples=["alice@example.com"])
    password: str   = Field(..., examples=["Secure1!"])

    @field_validator("email")
    @classmethod
    def email_to_lowercase(cls, v: str) -> str:
        return v.strip().lower()


class RefreshRequest(BaseModel):
    """Payload for POST /auth/refresh."""

    refresh_token: str = Field(
        ...,
        description="The refresh token received at login.",
    )


# ── Output schemas ────────────────────────────────────────────────────────────
class UserPublic(BaseModel):
    """Minimal user info embedded in token responses."""

    id:         int
    email:      str
    first_name: str | None = None
    last_name:  str | None = None
    is_active:  bool

    model_config = {"from_attributes": True}


class TokenResponse(BaseModel):
    """
    Standard response for login and refresh endpoints.

    The frontend must:
      1. Store access_token in memory (NOT localStorage).
      2. Store refresh_token in an httpOnly cookie (or secure storage).
      3. Use access_token as: Authorization: Bearer <access_token>
    """

    access_token:  str
    refresh_token: str
    token_type:    str = "Bearer"
    expires_in:    int = Field(
        description="Access token lifetime in seconds.",
    )
    user: UserPublic


class MessageResponse(BaseModel):
    """Simple confirmation message."""

    message: str
    success: bool = True
