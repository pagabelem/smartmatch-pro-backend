from datetime import datetime, timedelta, timezone
from jose import JWTError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

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


# ── Helpers ───────────────────────────────────────────────────────────────────
async def _build_token_pair(user: User, db: AsyncSession,
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
    await db.commit()

    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer",
        "expires_in": settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        "user": user,
    }


# ── Public service functions ──────────────────────────────────────────────────
async def register(db: AsyncSession, payload: RegisterRequest, user_agent: str | None = None, ip_address: str | None = None) -> dict:
    result = await db.execute(select(User).where(User.email == payload.email))
    existing = result.scalar_one_or_none()
    
    if existing:
        raise EmailAlreadyExistsException(payload.email)

    user = User(
        email=payload.email,
        hashed_password=hash_password(payload.password),
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)

    profile = Profile(
        user_id=user.id,
        first_name=payload.first_name,
        last_name=payload.last_name,
    )
    db.add(profile)
    await db.commit()
    await db.refresh(user)

    return await _build_token_pair(user, db, user_agent, ip_address)


async def login(db: AsyncSession, payload: LoginRequest, user_agent: str | None = None, ip_address: str | None = None) -> dict:
    result = await db.execute(select(User).where(User.email == payload.email))
    user = result.scalar_one_or_none()

    if not user or not verify_password(payload.password, user.hashed_password):
        raise InvalidCredentialsException()

    if not user.is_active:
        raise InvalidCredentialsException("Account is deactivated.")

    user.last_login_at = datetime.now(timezone.utc)
    await db.commit()
    await db.refresh(user)

    return await _build_token_pair(user, db, user_agent, ip_address)


async def refresh(db: AsyncSession, refresh_token_str: str, user_agent: str | None = None, ip_address: str | None = None) -> dict:
    try:
        payload = decode_refresh_token(refresh_token_str)
    except JWTError:
        raise InvalidTokenException("Refresh token is invalid or expired.")

    user_id = int(payload["sub"])

    result = await db.execute(
        select(RefreshToken).where(
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
    if db_token.expires_at.tzinfo is None:
        db_token_expiry = db_token.expires_at.replace(tzinfo=timezone.utc)
    else:
        db_token_expiry = db_token.expires_at

    if db_token_expiry < now:
        raise InvalidTokenException("Refresh token has expired.")

    db_token.is_revoked = True
    await db.commit()

    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    
    if not user or not user.is_active:
        raise NotFoundException("User", user_id)

    return await _build_token_pair(user, db, user_agent, ip_address)


async def logout(db: AsyncSession, refresh_token_str: str) -> None:
    result = await db.execute(select(RefreshToken).where(RefreshToken.token == refresh_token_str))
    db_token = result.scalar_one_or_none()
    
    if db_token:
        db_token.is_revoked = True
        await db.commit()


async def logout_all(db: AsyncSession, user_id: int) -> None:
    result = await db.execute(
        select(RefreshToken).where(
            RefreshToken.user_id == user_id,
            RefreshToken.is_revoked == False,
        )
    )
    tokens = result.scalars().all()
    
    for token in tokens:
        token.is_revoked = True
    
    await db.commit()


async def get_current_user_from_token(db: AsyncSession, token: str) -> User | None:
    """
    Récupère l'utilisateur à partir du token JWT.
    """
    from app.core.security import decode_access_token
    
    try:
        payload = decode_access_token(token)
    except JWTError:
        return None

    user_id = int(payload["sub"])
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    
    if not user:
        return None
        
    if not user.is_active:
        return None
        
    return user


async def change_password(db: AsyncSession, user: User, old_password: str, new_password: str) -> bool:
    """
    Change user password.
    
    Args:
        db: Database session
        user: User object
        old_password: Current password
        new_password: New password
    
    Returns:
        True if password changed successfully
    
    Raises:
        InvalidCredentialsException: If old password is incorrect
    """
    if not verify_password(old_password, user.hashed_password):
        raise InvalidCredentialsException("Current password is incorrect")
    
    user.hashed_password = hash_password(new_password)
    await db.commit()
    
    return True