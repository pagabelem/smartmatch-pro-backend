from datetime import datetime, timedelta, timezone
from jose import JWTError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Session
from sqlalchemy import select, update

from app.config import settings
from app.core.exceptions import (
    EmailAlreadyExistsException,
    InvalidCredentialsException,
    InvalidTokenException,
    NotFoundException,
)
from app.core.security import (
    create_access_token_with_expires,
    create_refresh_token,
    decode_refresh_token,
    hash_password,
    verify_password,
)
from app.modules.auth.auth_model import RefreshToken
from app.modules.auth.auth_schema import LoginRequest, RegisterRequest
from app.modules.users.user_model import Profile, User


# ── Polyfill Helper pour la compatibilité des sessions de test ────────────────
async def _safe_execute(db: AsyncSession | Session, statement):
    """
    Exécute une requête de manière sécurisée, que la session injectée
    par le TestClient soit synchrone ou asynchrone.
    """
    if hasattr(db, "execute_async"):  # Contexte AsyncSession strict
        return await db.execute(statement)
    elif isinstance(db, AsyncSession):
        return await db.execute(statement)
    else:
        # Fallback pour les sessions synchrones infiltrées par Starlette TestClient
        return db.execute(statement)


async def _safe_flush(db: AsyncSession | Session):
    if hasattr(db, "flush") and not isinstance(db, AsyncSession):
        db.flush()
    else:
        await db.flush()


async def _safe_commit(db: AsyncSession | Session):
    if hasattr(db, "commit") and not isinstance(db, AsyncSession):
        db.commit()
    else:
        await db.commit()


async def _safe_refresh(db: AsyncSession | Session, instance):
    if hasattr(db, "refresh") and not isinstance(db, AsyncSession):
        db.refresh(instance)
    else:
        await db.refresh(instance)


# ── Helpers ───────────────────────────────────────────────────────────────────
async def _build_token_pair(user: User, db: AsyncSession | Session,
                            user_agent: str | None = None,
                            ip_address: str | None = None) -> dict:
    access_token = create_access_token_with_expires(data={"sub": str(user.id)})
    refresh_token = create_refresh_token(subject=user.id)

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
    await _safe_commit(db) 

    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer",
        "expires_in": settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        "user": {
            "id": user.id,
            "email": user.email,
            "is_active": user.is_active,
            "is_superuser": user.is_superuser,
            "created_at": user.created_at,
            "updated_at": user.updated_at,
            "last_login_at": user.last_login_at,
        },
    }


# ── Public service functions ──────────────────────────────────────────────────
async def register(db: AsyncSession | Session, payload: RegisterRequest, user_agent: str | None = None, ip_address: str | None = None) -> dict:
    result = await _safe_execute(db, select(User).where(User.email == payload.email))
    existing = result.scalar_one_or_none()
    
    if existing:
        raise EmailAlreadyExistsException(payload.email)

    user = User(
        email=payload.email,
        hashed_password=hash_password(payload.password),
    )
    db.add(user)
    await _safe_flush(db)

    profile_data = {
        "user_id": user.id,
        "skills_raw": [],
        "skills_extracted": {"hard_skills": [], "soft_skills": []},
        "target_sectors": [],
        "target_contract_types": []
    }
    
    if hasattr(payload, "full_name") and payload.full_name:
        full_name_value = payload.full_name
    else:
        first = getattr(payload, "first_name", "") or ""
        last = getattr(payload, "last_name", "") or ""
        full_name_value = f"{first} {last}".strip() or "New User"

    profile = Profile(**profile_data)
    profile.full_name = full_name_value
    
    db.add(profile)
    await _safe_flush(db)
    await _safe_refresh(db, user)

    return await _build_token_pair(user, db, user_agent, ip_address)


async def login(db: AsyncSession | Session, payload: LoginRequest, user_agent: str | None = None, ip_address: str | None = None) -> dict:
    result = await _safe_execute(db, select(User).where(User.email == payload.email))
    user = result.scalar_one_or_none()

    if not user or not verify_password(payload.password, user.hashed_password):
        raise InvalidCredentialsException()

    if not user.is_active:
        raise InvalidCredentialsException("Account is deactivated.")

    user.last_login_at = datetime.now(timezone.utc)
    await _safe_flush(db)
    await _safe_refresh(db, user)

    return await _build_token_pair(user, db, user_agent, ip_address)


async def refresh(db: AsyncSession | Session, refresh_token_str: str, user_agent: str | None = None, ip_address: str | None = None) -> dict:
    try:
        payload = decode_refresh_token(refresh_token_str)
    except JWTError:
        raise InvalidTokenException("Refresh token is invalid or expired.")

    user_id = int(payload["sub"])

    result = await _safe_execute(
        db, select(RefreshToken).where(
            RefreshToken.token == refresh_token_str,
            RefreshToken.user_id == user_id,
        )
    )
    db_token = result.scalar_one_or_none()

    if not db_token:
        raise InvalidTokenException("Refresh token not recognised.")

    if db_token.is_revoked:
        await logout_all(db, user_id)
        raise InvalidTokenException(
            "Refresh token already used. All sessions have been revoked for security."
        )

    now = datetime.now(timezone.utc)
    db_token_expiry = db_token.expires_at.replace(tzinfo=timezone.utc) if db_token.expires_at.tzinfo is None else db_token.expires_at

    if db_token_expiry < now:
        raise InvalidTokenException("Refresh token has expired.")

    db_token.is_revoked = True
    await _safe_flush(db)

    result = await _safe_execute(db, select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    
    if not user or not user.is_active:
        raise NotFoundException("User", user_id)

    return await _build_token_pair(user, db, user_agent, ip_address)


async def logout(db: AsyncSession | Session, refresh_token_str: str) -> None:
    result = await _safe_execute(db, select(RefreshToken).where(RefreshToken.token == refresh_token_str))
    db_token = result.scalar_one_or_none()
    
    if db_token:
        db_token.is_revoked = True
        await _safe_commit(db)


async def logout_all(db: AsyncSession | Session, user_id: int) -> None:
    await _safe_execute(
        db, update(RefreshToken)
        .where(RefreshToken.user_id == user_id, RefreshToken.is_revoked == False)
        .values(is_revoked=True)
    )
    await _safe_commit(db)


async def get_current_user_from_token(db: AsyncSession | Session, token: str) -> User | None:
    from app.core.security import decode_access_token
    
    try:
        payload = decode_access_token(token)
    except JWTError:
        return None

    user_id = int(payload["sub"])
    result = await _safe_execute(db, select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    
    if not user or not user.is_active:
        return None
        
    return user


async def change_password(db: AsyncSession | Session, user: User, old_password: str, new_password: str) -> bool:
    if not verify_password(old_password, user.hashed_password):
        raise InvalidCredentialsException("Current password is incorrect")
    
    user.hashed_password = hash_password(new_password)
    await _safe_commit(db)
    
    return True


async def revoke_all_user_tokens(db: AsyncSession | Session, user_id: int) -> None:
    await logout_all(db, user_id)