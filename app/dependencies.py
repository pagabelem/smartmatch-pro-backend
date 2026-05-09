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

# ── OAuth2 scheme (tells Swagger UI where to get the token) ───────────────────
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")


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
# NOTE: This is intentionally a forward-compatible stub.
# Phase 1 (auth module) will replace the body with real JWT validation.
# The signature is already correct so every module that imports it won't break.

def get_current_user(
    db: Session = Depends(get_db),
    token: str = Depends(oauth2_scheme),
):
    """
    Decode the JWT bearer token and return the authenticated User.

    STUB — implemented fully in Phase 1 (app/modules/auth/auth_service.py).
    Raises HTTP 401 if the token is invalid or the user no longer exists.
    """
    # Phase 1 will import and call:
    #   from app.core.security import decode_access_token
    #   from app.modules.users.user_model import User
    #   payload = decode_access_token(token)
    #   user = db.get(User, payload["sub"])
    #   if not user or not user.is_active:
    #       raise HTTPException(status_code=401, detail="Invalid credentials")
    #   return user

    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail="Auth module not yet implemented (Phase 1).",
    )


def get_current_active_user(current_user=Depends(get_current_user)):
    """
    Same as get_current_user but also enforces is_active=True.
    Raises HTTP 400 if the account is deactivated.
    """
    if not getattr(current_user, "is_active", True):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Inactive user account.",
        )
    return current_user


"""
dependencies.py — FastAPI dependency functions.

Phase 1 update: get_current_user now performs real JWT validation
using auth_service.get_current_user_from_token().
"""

from typing import Generator

from fastapi import Depends, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from app.core.exceptions import InvalidTokenException
from app.database import SessionLocal

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")


def get_db() -> Generator[Session, None, None]:
    """Yield a SQLAlchemy Session, close it after the request."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def get_current_user(
    db: Session = Depends(get_db),
    token: str = Depends(oauth2_scheme),
):
    """
    Decode the JWT access token and return the authenticated User.

    Raises HTTP 401 if the token is invalid, expired, or the user no longer exists.
    """
    from app.modules.auth.auth_service import get_current_user_from_token
    return get_current_user_from_token(db, token)


def get_current_active_user(current_user=Depends(get_current_user)):
    """Same as get_current_user but also enforces is_active=True."""
    if not getattr(current_user, "is_active", True):
        raise InvalidTokenException("Account is deactivated.")
    return current_user


def get_current_superuser(current_user=Depends(get_current_user)):
    """Restrict endpoint to superusers (admins)."""
    from app.core.exceptions import ForbiddenException
    if not getattr(current_user, "is_superuser", False):
        raise ForbiddenException("Superuser access required.")
    return current_user
