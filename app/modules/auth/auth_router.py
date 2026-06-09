from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.modules.auth.auth_schema import (
    RegisterRequest, 
    LoginRequest, 
    ChangePasswordRequest,
)
from app.modules.auth.auth_service import (
    register, login, refresh, logout, 
    get_current_user_from_token, change_password
)
from app.core.responses import success_response, ok, error_response
from app.core.exceptions import InvalidCredentialsException, EmailAlreadyExistsException, InvalidTokenException

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post("/register", status_code=status.HTTP_201_CREATED)
async def register_user(
    payload: RegisterRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    try:
        result = await register(
            db=db,
            payload=payload,
            user_agent=request.headers.get("user-agent"),
            ip_address=request.client.host if request.client else None,
        )
        return success_response(data=result, message="Account created successfully.")
    except EmailAlreadyExistsException as e:
        # Utilisation de HTTPException pour garantir le statut HTTP réel auprès de Pytest
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={"message": str(e), "code": "EMAIL_EXISTS"}
        )


@router.post("/login")
async def login_user(
    payload: LoginRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    try:
        result = await login(
            db=db,
            payload=payload,
            user_agent=request.headers.get("user-agent"),
            ip_address=request.client.host if request.client else None,
        )
        return success_response(data=result, message="Login successful.")
    except InvalidCredentialsException as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"message": str(e), "code": "INVALID_CREDENTIALS"}
        )


@router.post("/refresh")
async def refresh_token(
    refresh_token: str,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    try:
        result = await refresh(
            db=db,
            refresh_token_str=refresh_token,
            user_agent=request.headers.get("user-agent"),
            ip_address=request.client.host if request.client else None,
        )
        return success_response(data=result, message="Token refreshed.")
    except InvalidTokenException as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"message": str(e), "code": "INVALID_TOKEN"}
        )


@router.post("/logout")
async def logout_user(
    refresh_token: str,
    db: AsyncSession = Depends(get_db),
):
    await logout(db=db, refresh_token_str=refresh_token)
    return ok(message="Logged out successfully.")


@router.get("/me")
async def get_current_user_info(
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    auth_header = request.headers.get("Authorization")
    if not auth_header or not auth_header.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"message": "Missing token", "code": "UNAUTHORIZED"}
        )
        
    token = auth_header.split(" ")[1]
    current_user = await get_current_user_from_token(db, token)
    
    if not current_user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"message": "Invalid or expired token", "code": "UNAUTHORIZED"}
        )
        
    # Transformation de l'objet SQLAlchemy en dictionnaire pour la réponse JSON
    return success_response(data={
        "id": current_user.id,
        "email": current_user.email,
        "is_active": current_user.is_active,
        "is_superuser": current_user.is_superuser
    })


@router.post("/change-password")
async def change_user_password(
    payload: ChangePasswordRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    auth_header = request.headers.get("Authorization")
    if not auth_header or not auth_header.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"message": "Missing token", "code": "UNAUTHORIZED"}
        )
        
    token = auth_header.split(" ")[1]
    current_user = await get_current_user_from_token(db, token)
    
    if not current_user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"message": "Invalid or expired token", "code": "UNAUTHORIZED"}
        )
        
    try:
        result = await change_password(
            db=db,
            user=current_user,
            old_password=payload.old_password,
            new_password=payload.new_password,
        )
        return success_response(data=result, message="Password changed successfully.")
    except InvalidCredentialsException as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"message": str(e), "code": "BAD_REQUEST"}
        )