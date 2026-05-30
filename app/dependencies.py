"""
dependencies.py — FastAPI dependency functions.

These are injected into route handlers via Depends().

Usage
-----
  from app.dependencies import get_db, get_current_user
  from sqlalchemy.orm import Session
  from fastapi import Depends

  @router.get("/me")
  def read_me(db: Session = Depends(get_db), current_user = Depends(get_current_user)):
      ...
"""

from typing import Generator

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from app.database import SessionLocal
from app.core.exceptions import UnauthorizedException, ForbiddenException

# ── OAuth2 scheme (tells Swagger UI where to get the token) ───────────────────
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login", auto_error=False)


# ── Database session ──────────────────────────────────────────────────────────
def get_db() -> Generator[Session, None, None]:
    """
    Yield a SQLAlchemy Session for the duration of a single request,
    then close it automatically — even if an exception occurs.

    Usage:
        @router.get("/items")
        def list_items(db: Session = Depends(get_db)):
            return db.query(Item).all()
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# ── Current authenticated user ────────────────────────────────────────────────
def get_current_user(
    db: Session = Depends(get_db),
    token: str = Depends(oauth2_scheme),
):
    """
    Decode the JWT bearer token and return the authenticated User.

    Raises HTTP 401 if the token is invalid or the user no longer exists.
    """
    from app.modules.auth.auth_service import get_current_user_from_token
    return get_current_user_from_token(db, token)


def get_current_active_user(current_user = Depends(get_current_user)):
    """Same as get_current_user but also enforces is_active=True."""
    if not getattr(current_user, "is_active", True):
        raise UnauthorizedException("Account is deactivated.")
    return current_user


def get_current_admin_user(current_user = Depends(get_current_user)):
    """Restrict endpoint to admin users (is_superuser=True)."""
    if not getattr(current_user, "is_superuser", False):
        raise ForbiddenException("Admin access required.")
    return current_user


def get_current_superuser(current_user = Depends(get_current_user)):
    """Alias for get_current_admin_user."""
    return get_current_admin_user(current_user)

# app/dependencies.py - ajoute cette fonction

def get_db_session():
    """Return database session without type annotation for FastAPI."""
    return get_db()

# app/dependencies.py
from app.database import SessionLocal

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()