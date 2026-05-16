"""
core/security.py — Password hashing (passlib) and JWT utilities (python-jose).

This module is STATELESS — it only contains pure functions.
It knows nothing about the database or HTTP.

Usage
-----
  from app.core.security import hash_password, verify_password
  from app.core.security import create_access_token, decode_access_token
"""
from passlib.context import CryptContext

# Change your current initialization to this:
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

from datetime import datetime, timedelta, timezone
from typing import Any

from jose import JWTError, jwt
from passlib.context import CryptContext

from app.config import settings

# ── Password hashing ──────────────────────────────────────────────────────────
# bcrypt is the recommended algorithm for passwords.
# deprecated="auto" automatically upgrades hashes from older schemes on login.
_pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(plain_password: str) -> str:
    """
    Hash a plain-text password with bcrypt.

    Example:
        hashed = hash_password("mySecret123")
    """
    return _pwd_context.hash(plain_password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Verify a plain-text password against a stored bcrypt hash.

    Returns True if they match, False otherwise.
    Never raises — always returns a boolean.

    Example:
        if not verify_password(form.password, user.hashed_password):
            raise HTTPException(401, "Invalid credentials")
    """
    return _pwd_context.verify(plain_password, hashed_password)


# ── JWT helpers ───────────────────────────────────────────────────────────────
# Token structure:
#   {
#     "sub":  "42",          ← user ID (always a string)
#     "type": "access",      ← "access" or "refresh"
#     "iat":  1700000000,    ← issued-at (set automatically)
#     "exp":  1700003600,    ← expiry   (set automatically)
#   }


def create_access_token(subject: int | str, extra_claims: dict[str, Any] | None = None) -> str:
    """
    Create a signed JWT access token.

    Parameters
    ----------
    subject:
        The user's ID. Will be stored as ``sub`` (always coerced to str).
    extra_claims:
        Optional additional payload data (e.g. {"role": "admin"}).

    Returns
    -------
    str
        Signed JWT string ready to send to the client.

    Example:
        token = create_access_token(subject=user.id)
    """
    expire = datetime.now(timezone.utc) + timedelta(
        minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES
    )
    payload: dict[str, Any] = {
        "sub": str(subject),
        "type": "access",
        "iat": datetime.now(timezone.utc),
        "exp": expire,
    }
    if extra_claims:
        payload.update(extra_claims)

    return jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


def create_refresh_token(subject: int | str) -> str:
    """
    Create a longer-lived refresh token.

    Used to obtain a new access token without re-authenticating.
    Store refresh tokens server-side (e.g. in DB) to allow revocation.
    """
    expire = datetime.now(timezone.utc) + timedelta(
        days=settings.REFRESH_TOKEN_EXPIRE_DAYS
    )
    payload: dict[str, Any] = {
        "sub": str(subject),
        "type": "refresh",
        "iat": datetime.now(timezone.utc),
        "exp": expire,
    }
    return jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


def decode_access_token(token: str) -> dict[str, Any]:
    """
    Decode and validate a JWT access token.

    Returns the raw payload dict on success.
    Raises ``JWTError`` (from python-jose) on any failure:
      - expired token
      - invalid signature
      - malformed token
      - wrong token type

    The caller (get_current_user in dependencies.py) is responsible for
    catching JWTError and converting it to an HTTP 401 response.

    Example:
        try:
            payload = decode_access_token(token)
            user_id = int(payload["sub"])
        except JWTError:
            raise HTTPException(401, "Could not validate credentials")
    """
    payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])

    # Guard: refuse refresh tokens used as access tokens
    if payload.get("type") != "access":
        raise JWTError("Invalid token type.")

    return payload


def decode_refresh_token(token: str) -> dict[str, Any]:
    """Same as decode_access_token but validates type == 'refresh'."""
    payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
    if payload.get("type") != "refresh":
        raise JWTError("Invalid token type.")
    return payload