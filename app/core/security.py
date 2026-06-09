"""
core/security.py — Password hashing (bcrypt pur) and JWT utilities (python-jose).

This module is STATELESS — it only contains pure functions.
It knows nothing about the database or HTTP.
"""
import uuid
import bcrypt
from datetime import datetime, timedelta, timezone
from typing import Any, Optional

from jose import JWTError, jwt
from app.config import settings

# ── Password hashing (Bcrypt Pur sans Passlib) ───────────────────────────────

def hash_password(plain_password: str) -> str:
    """Hash a plain-text password with bcrypt."""
    password_bytes = plain_password.encode('utf-8')
    salt = bcrypt.gensalt()
    hashed_bytes = bcrypt.hashpw(password_bytes, salt)
    return hashed_bytes.decode('utf-8')


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a plain-text password against a stored bcrypt hash."""
    try:
        password_bytes = plain_password.encode('utf-8')
        hashed_bytes = hashed_password.encode('utf-8')
        return bcrypt.checkpw(password_bytes, hashed_bytes)
    except Exception:
        return False


# Alias pour les tests (get_password_hash = hash_password)
get_password_hash = hash_password


# ── JWT helpers ───────────────────────────────────────────────────────────────

def create_access_token(
    subject_or_data: Any = None,
    extra_claims: Optional[dict[str, Any]] = None,
    expires_delta: Optional[timedelta] = None,
    **kwargs
) -> str:
    """
    Create a signed JWT access token.

    Usage:
        # Avec subject (int/str)
        token = create_access_token(42, extra_claims={"role": "admin"})

        # Avec data dict
        token = create_access_token({"sub": 42, "role": "admin"})

        # Avec expires_delta custom
        token = create_access_token(42, expires_delta=timedelta(minutes=5))
    """
    # Déterminer le payload de base
    if isinstance(subject_or_data, dict):
        # Mode data dict
        payload = subject_or_data.copy()
        if "sub" in payload:
            payload["sub"] = str(payload["sub"])
    elif subject_or_data is not None:
        # Mode subject
        payload = {
            "sub": str(subject_or_data),
            "type": "access",
            "iat": datetime.now(timezone.utc),
            "jti": str(uuid.uuid4()),
        }
        if extra_claims:
            payload.update(extra_claims)
    else:
        # Mode kwargs
        if "data" in kwargs:
            payload = kwargs["data"].copy()
            if "sub" in payload:
                payload["sub"] = str(payload["sub"])
        elif "subject" in kwargs:
            payload = {
                "sub": str(kwargs["subject"]),
                "type": "access",
                "iat": datetime.now(timezone.utc),
                "jti": str(uuid.uuid4()),
            }
            if extra_claims:
                payload.update(extra_claims)
        else:
            payload = {"sub": "1", "type": "access"}

    # Définir l'expiration
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)

    payload["exp"] = expire
    payload["type"] = payload.get("type", "access")

    return jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


# ✅ ALIAS pour compatibilité avec auth_service.py
def create_access_token_with_expires(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """
    Alias pour compatibilité avec le code existant.
    Utilise create_access_token universel.
    """
    return create_access_token(data, expires_delta=expires_delta)


# ✅ ALIAS pour compatibilité avec auth_service.py
def create_access_token_from_data(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """
    Alias pour compatibilité avec le code existant.
    Utilise create_access_token universel.
    """
    return create_access_token(data, expires_delta=expires_delta)


# ✅ ALIAS pour compatibilité avec auth_service.py
def create_access_token_flexible(subject_or_data: Any, extra_claims: Optional[dict] = None) -> str:
    """
    Alias pour compatibilité avec le code existant.
    Utilise create_access_token universel.
    """
    return create_access_token(subject_or_data, extra_claims=extra_claims)


def create_refresh_token(subject: int | str) -> str:
    """
    Create a longer-lived refresh token.
    """
    expire = datetime.now(timezone.utc) + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
    payload = {
        "sub": str(subject),
        "type": "refresh",
        "iat": datetime.now(timezone.utc),
        "exp": expire,
        "jti": str(uuid.uuid4()),
    }
    return jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


def decode_access_token(token: str) -> dict[str, Any]:
    """Decode and validate a JWT access token."""
    payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
    if payload.get("type") != "access":
        raise JWTError("Invalid token type.")
    return payload


def decode_refresh_token(token: str) -> dict[str, Any]:
    """Decode and validate a JWT refresh token."""
    payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
    if payload.get("type") != "refresh":
        raise JWTError("Invalid token type.")
    return payload


def decode_token(token: str) -> dict[str, Any]:
    """Decode and validate a JWT token (generic)."""
    return jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])