from datetime import datetime, timedelta, timezone
from jose import JWTError
from sqlalchemy.orm import Session

from app.config import settings
from app.core.exceptions import (
    EmailAlreadyExistsException,
    InvalidCredentialsException,
    InvalidTokenException,
    NotFoundException,
)
from app.core.security import (
    create_access_token,
    create_refresh_token,
    decode_refresh_token,
    hash_password,
    verify_password,
)
from app.modules.auth.auth_model import RefreshToken
from app.modules.auth.auth_schema import LoginRequest, RegisterRequest
from app.modules.users.user_model import Profile, User

# ── Helpers ───────────────────────────────────────────────────────────────────
def _build_token_pair(user: User, db: Session,
                      user_agent: str | None = None,
                      ip_address: str | None = None) -> dict:
    access_token  = create_access_token(subject=user.id)
    refresh_token = create_refresh_token(subject=user.id)

    # Utilisation de UTC pour la cohérence
    expires_at = datetime.now(timezone.utc) + timedelta(
        days=settings.REFRESH_TOKEN_EXPIRE_DAYS
    )

    db_token = RefreshToken(
        token=refresh_token,
        user_id=user.id,
        expires_at=expires_at,
        user_agent=user_agent,
        ip_address=ip_address,
    )
    db.add(db_token)
    db.commit()

    return {
        "access_token":  access_token,
        "refresh_token": refresh_token,
        "token_type":    "Bearer",
        "expires_in":    settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        "user":          user,
    }

# ── Public service functions ──────────────────────────────────────────────────
def register(db: Session, payload: RegisterRequest, user_agent: str | None = None, ip_address: str | None = None) -> dict:
    existing = db.query(User).filter(User.email == payload.email).first()
    if existing:
        raise EmailAlreadyExistsException(payload.email)

    user = User(
        email=payload.email,
        hashed_password=hash_password(payload.password),
    )
    db.add(user)
    db.flush()

    profile = Profile(
        user_id=user.id,
        first_name=payload.first_name,
        last_name=payload.last_name,
    )
    db.add(profile)
    db.commit()
    db.refresh(user)

    return _build_token_pair(user, db, user_agent, ip_address)

def login(db: Session, payload: LoginRequest, user_agent: str | None = None, ip_address: str | None = None) -> dict:
    user = db.query(User).filter(User.email == payload.email).first()

    if not user or not verify_password(payload.password, user.hashed_password):
        raise InvalidCredentialsException()

    if not user.is_active:
        raise InvalidCredentialsException("Account is deactivated.")

    user.last_login_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(user)

    return _build_token_pair(user, db, user_agent, ip_address)

def refresh(db: Session, refresh_token_str: str, user_agent: str | None = None, ip_address: str | None = None) -> dict:
    try:
        payload = decode_refresh_token(refresh_token_str)
    except JWTError:
        raise InvalidTokenException("Refresh token is invalid or expired.")

    user_id = int(payload["sub"])

    db_token = (
        db.query(RefreshToken)
        .filter(
            RefreshToken.token == refresh_token_str,
            RefreshToken.user_id == user_id,
        )
        .first()
    )

    if not db_token:
        raise InvalidTokenException("Refresh token not recognised.")

    if db_token.is_revoked:
        logout_all(db, user_id)
        raise InvalidTokenException(
            "Refresh token already used. All sessions have been revoked for security."
        )

    # FIX: Comparaison sécurisée entre Aware (timezone.utc) et Naive (DB)
    now = datetime.now(timezone.utc)
    # On s'assure que db_token.expires_at est traité comme aware pour la comparaison
    if db_token.expires_at.tzinfo is None:
        db_token_expiry = db_token.expires_at.replace(tzinfo=timezone.utc)
    else:
        db_token_expiry = db_token.expires_at

    if db_token_expiry < now:
        raise InvalidTokenException("Refresh token has expired.")

    db_token.is_revoked = True
    db.commit()

    user = db.get(User, user_id)
    if not user or not user.is_active:
        raise NotFoundException("User", user_id)

    return _build_token_pair(user, db, user_agent, ip_address)

def logout(db: Session, refresh_token_str: str) -> None:
    db_token = db.query(RefreshToken).filter(RefreshToken.token == refresh_token_str).first()
    if db_token:
        db_token.is_revoked = True
        db.commit()

def logout_all(db: Session, user_id: int) -> None:
    db.query(RefreshToken).filter(
        RefreshToken.user_id == user_id,
        RefreshToken.is_revoked == False,
    ).update({"is_revoked": True})
    db.commit()

def get_current_user_from_token(db: Session, token: str) -> User:
    from app.core.security import decode_access_token
    try:
        payload = decode_access_token(token)
    except JWTError:
        raise InvalidTokenException()

    user_id = int(payload["sub"])
    user = db.get(User, user_id)
    if not user:
        raise NotFoundException("User", user_id)
    if not user.is_active:
        raise InvalidTokenException("Account is deactivated.")
    return user