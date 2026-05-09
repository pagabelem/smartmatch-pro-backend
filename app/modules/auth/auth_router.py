from fastapi import APIRouter, Depends, Request, status
from sqlalchemy.orm import Session

from app.core.responses import created, ok
from app.dependencies import get_current_active_user, get_db
from app.modules.auth import auth_service
from app.modules.auth.auth_schema import (
    LoginRequest,
    MessageResponse,
    RefreshRequest,
    RegisterRequest,
    TokenResponse,
    UserPublic,
)

router = APIRouter()

# ── POST /register ────────────────────────────────────────────────────────────
@router.post(
    "/register",
    status_code=status.HTTP_201_CREATED,
    response_model=TokenResponse,
    summary="Register a new account",
)
def register(
    payload: RegisterRequest,
    request: Request,
    db: Session = Depends(get_db),
) -> TokenResponse:
    result = auth_service.register(
        db=db,
        payload=payload,
        user_agent=request.headers.get("user-agent"),
        ip_address=request.client.host if request.client else None,
    )
    # Plus besoin de model_dump() manuel, le helper s'en charge via jsonable_encoder
    return created(data=result, message="Account created successfully.")


# ── POST /login ───────────────────────────────────────────────────────────────
@router.post(
    "/login",
    response_model=TokenResponse,
    summary="Login with email and password",
)
def login(
    payload: LoginRequest,
    request: Request,
    db: Session = Depends(get_db),
) -> TokenResponse:
    result = auth_service.login(
        db=db,
        payload=payload,
        user_agent=request.headers.get("user-agent"),
        ip_address=request.client.host if request.client else None,
    )
    return ok(data=result, message="Login successful.")


# ── POST /refresh ─────────────────────────────────────────────────────────────
@router.post(
    "/refresh",
    response_model=TokenResponse,
    summary="Refresh token pair",
)
def refresh(
    payload: RefreshRequest,
    request: Request,
    db: Session = Depends(get_db),
) -> TokenResponse:
    result = auth_service.refresh(
        db=db,
        refresh_token_str=payload.refresh_token,
        user_agent=request.headers.get("user-agent"),
        ip_address=request.client.host if request.client else None,
    )
    return ok(data=result, message="Token refreshed.")


# ── POST /logout ──────────────────────────────────────────────────────────────
@router.post(
    "/logout",
    response_model=MessageResponse,
    summary="Logout current device",
)
def logout(
    payload: RefreshRequest,
    db: Session = Depends(get_db),
) -> MessageResponse:
    auth_service.logout(db=db, refresh_token_str=payload.refresh_token)
    return ok(message="Logged out successfully.")


# ── POST /logout-all ──────────────────────────────────────────────────────────
@router.post(
    "/logout-all",
    response_model=MessageResponse,
    summary="Logout all devices",
)
def logout_all(
    db: Session = Depends(get_db),
    current_user=Depends(get_current_active_user),
) -> MessageResponse:
    auth_service.logout_all(db=db, user_id=current_user.id)
    return ok(message="All sessions have been revoked.")


# ── GET /me ───────────────────────────────────────────────────────────────────
@router.get(
    "/me",
    response_model=UserPublic,
    summary="Get current authenticated user",
)
def me(
    current_user=Depends(get_current_active_user),
) -> UserPublic:
    # On convertit le modèle SQLAlchemy en schéma Pydantic pour filtrer les champs
    user_data = UserPublic.model_validate(current_user)
    return ok(data=user_data)