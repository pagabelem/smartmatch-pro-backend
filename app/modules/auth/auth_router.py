from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.modules.auth.auth_schema import (
    RegisterRequest, 
    LoginRequest, 
    ChangePasswordRequest,
)
from app.modules.auth.auth_service import (
    register, login, refresh, logout, logout_all, 
    get_current_user_from_token, change_password
)
from app.core.responses import success_response, ok, error_response
from app.core.exceptions import InvalidCredentialsException, EmailAlreadyExistsException, InvalidTokenException

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post("/register", status_code=status.HTTP_201_CREATED)
async def register_user(  # ✅ async
    payload: RegisterRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),  # ✅ AsyncSession
):
    try:
        result = await register(  # ✅ await
            db=db,
            payload=payload,
            user_agent=request.headers.get("user-agent"),
            ip_address=request.client.host if request.client else None,
        )
        return success_response(data=result, message="Account created successfully.")
    except EmailAlreadyExistsException as e:
        return error_response(message=str(e), code="EMAIL_EXISTS"), status.HTTP_409_CONFLICT


@router.post("/login")
async def login_user(  # ✅ async
    payload: LoginRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),  # ✅ AsyncSession
):
    try:
        result = await login(  # ✅ await
            db=db,
            payload=payload,
            user_agent=request.headers.get("user-agent"),
            ip_address=request.client.host if request.client else None,
        )
        return success_response(data=result, message="Login successful.")
    except InvalidCredentialsException as e:
        return error_response(message=str(e), code="INVALID_CREDENTIALS"), status.HTTP_401_UNAUTHORIZED


@router.post("/refresh")
async def refresh_token(  # ✅ async
    refresh_token: str,
    request: Request,
    db: AsyncSession = Depends(get_db),  # ✅ AsyncSession
):
    try:
        result = await refresh(  # ✅ await
            db=db,
            refresh_token_str=refresh_token,
            user_agent=request.headers.get("user-agent"),
            ip_address=request.client.host if request.client else None,
        )
        return success_response(data=result, message="Token refreshed.")
    except InvalidTokenException as e:
        return error_response(message=str(e), code="INVALID_TOKEN"), status.HTTP_401_UNAUTHORIZED


@router.post("/logout")
async def logout_user(  # ✅ async
    refresh_token: str,
    db: AsyncSession = Depends(get_db),  # ✅ AsyncSession
):
    await logout(db=db, refresh_token_str=refresh_token)  # ✅ await
    return ok(message="Logged out successfully.")


@router.get("/me")
async def get_current_user_info(  # ✅ async
    request: Request,
    db: AsyncSession = Depends(get_db),  # ✅ AsyncSession
):
    auth_header = request.headers.get("Authorization")
    if not auth_header or not auth_header.startswith("Bearer "):
        return error_response(message="Missing token", code="UNAUTHORIZED"), status.HTTP_401_UNAUTHORIZED
    token = auth_header.split(" ")[1]
    current_user = await get_current_user_from_token(db, token)  # ✅ await
    return success_response(data=current_user)


@router.post("/change-password")
async def change_user_password(  # ✅ async
    payload: ChangePasswordRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),  # ✅ AsyncSession
):
    auth_header = request.headers.get("Authorization")
    if not auth_header or not auth_header.startswith("Bearer "):
        return error_response(message="Missing token", code="UNAUTHORIZED"), status.HTTP_401_UNAUTHORIZED
    token = auth_header.split(" ")[1]
    current_user = await get_current_user_from_token(db, token)  # ✅ await
    result = await change_password(  # ✅ await
        db=db,
        user=current_user,
        old_password=payload.old_password,
        new_password=payload.new_password,
    )
    return success_response(data=result, message="Password changed successfully.")