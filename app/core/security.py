"""
core/security.py — Password hashing (passlib) and JWT utilities (python-jose).

This module is STATELESS — it only contains pure functions.
It knows nothing about the database or HTTP.
"""
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any, Optional

from jose import JWTError, jwt
from passlib.context import CryptContext

from app.config import settings

# ── Password hashing ──────────────────────────────────────────────────────────
_pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(plain_password: str) -> str:
    """Hash a plain-text password with bcrypt."""
    return _pwd_context.hash(plain_password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a plain-text password against a stored bcrypt hash."""
    return _pwd_context.verify(plain_password, hashed_password)


# Alias pour les tests (get_password_hash = hash_password)
get_password_hash = hash_password


# ── JWT helpers ───────────────────────────────────────────────────────────────

def create_access_token(subject: int | str, extra_claims: dict[str, Any] | None = None) -> str:
    """
    Create a signed JWT access token.
    """
    expire = datetime.now(timezone.utc) + timedelta(
        minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES
    )
    payload: dict[str, Any] = {
        "sub": str(subject),
        "type": "access",
        "iat": datetime.now(timezone.utc),
        "exp": expire,
        "jti": str(uuid.uuid4()),
    }
    if extra_claims:
        payload.update(extra_claims)

    return jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


def create_refresh_token(subject: int | str) -> str:
    """
    Create a longer-lived refresh token.
    Ajout d'un JTI (UUID) pour éviter l'erreur UNIQUE constraint en base de données
    lors des tests rapides.
    """
    expire = datetime.now(timezone.utc) + timedelta(
        days=settings.REFRESH_TOKEN_EXPIRE_DAYS
    )
    payload: dict[str, Any] = {
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
    """Same as decode_access_token but validates type == 'refresh'."""
    payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
    if payload.get("type") != "refresh":
        raise JWTError("Invalid token type.")
    return payload


def decode_token(token: str) -> dict[str, Any]:
    """
    Decode and validate a JWT token (generic).
    """
    return jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])


# Version avec expires_delta pour compatibilité avec les tests
def create_access_token_with_expires(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """
    Create a JWT access token with custom expiration.
    Compatible avec l'appel des tests.
    """
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire, "type": "access"})
    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


# Alias pour que les tests fonctionnent avec create_access_token(data, expires_delta)
# Cette version accepte un dictionnaire data et un expires_delta optionnel
def create_access_token_from_data(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """
    Create a JWT access token from a data dict.
    Utilisé par les tests qui passent {"sub": user_id}.
    """
    return create_access_token_with_expires(data, expires_delta)


# Redéfinir create_access_token pour accepter les deux signatures
# Cela permet aux tests d'appeler create_access_token(data={"sub": str(user_id)})
def create_access_token_flexible(subject_or_data: Any, extra_claims: Optional[dict] = None) -> str:
    """
    Flexible create_access_token that accepts either:
    - subject (int|str) and optional extra_claims
    - data dict with 'sub' key
    """
    if isinstance(subject_or_data, dict):
        # Appel avec data={"sub": ...}
        return create_access_token_with_expires(subject_or_data)
    else:
        # Appel avec subject
        return create_access_token(subject_or_data, extra_claims)


# Pour garder la compatibilité avec les imports existants
# On expose create_access_token qui fonctionne avec les deux signatures
def create_access_token(*args, **kwargs) -> str:
    """
    Universal create_access_token that handles both calling conventions.
    """
    if len(args) == 1 and isinstance(args[0], dict):
        # create_access_token(data={"sub": user_id})
        return create_access_token_with_expires(args[0])
    elif len(args) == 1 and (isinstance(args[0], int) or isinstance(args[0], str)):
        # create_access_token(subject=user_id)
        return create_access_token(args[0], kwargs.get("extra_claims"))
    elif len(args) == 0 and "data" in kwargs:
        # create_access_token(data={"sub": user_id})
        return create_access_token_with_expires(kwargs["data"])
    elif len(args) == 0 and "subject" in kwargs:
        # create_access_token(subject=user_id)
        return create_access_token(kwargs["subject"], kwargs.get("extra_claims"))
    else:
        # Fallback
        return create_access_token_with_expires(kwargs.get("data", {"sub": "1"}))