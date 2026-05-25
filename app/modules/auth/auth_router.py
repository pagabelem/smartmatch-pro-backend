from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.orm import Session

from app.dependencies import get_db
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
def register_user(
    payload: RegisterRequest,
    request: Request,
    db: Session = Depends(get_db),
):
    try:
        result = register(
            db=db,
            payload=payload,
            user_agent=request.headers.get("user-agent"),
            ip_address=request.client.host if request.client else None,
        )
        return success_response(data=result, message="Account created successfully.")
    except EmailAlreadyExistsException as e:
        return error_response(message=str(e), code="EMAIL_EXISTS"), status.HTTP_409_CONFLICT


@router.post("/login")
def login_user(
    payload: LoginRequest,
    request: Request,
    db: Session = Depends(get_db),
):
    try:
        result = login(
            db=db,
            payload=payload,
            user_agent=request.headers.get("user-agent"),
            ip_address=request.client.host if request.client else None,
        )
        return success_response(data=result, message="Login successful.")
    except InvalidCredentialsException as e:
        return error_response(message=str(e), code="INVALID_CREDENTIALS"), status.HTTP_401_UNAUTHORIZED


@router.post("/refresh")
def refresh_token(
    refresh_token: str,
    request: Request,
    db: Session = Depends(get_db),
):
    try:
        result = refresh(
            db=db,
            refresh_token_str=refresh_token,
            user_agent=request.headers.get("user-agent"),
            ip_address=request.client.host if request.client else None,
        )
        return success_response(data=result, message="Token refreshed.")
    except InvalidTokenException as e:
        return error_response(message=str(e), code="INVALID_TOKEN"), status.HTTP_401_UNAUTHORIZED


@router.post("/logout")
def logout_user(
    refresh_token: str,
    db: Session = Depends(get_db),
):
    logout(db=db, refresh_token_str=refresh_token)
    return ok(message="Logged out successfully.")


@router.get("/me")
def get_current_user_info(
    request: Request,
    db: Session = Depends(get_db),
):
    auth_header = request.headers.get("Authorization")
    if not auth_header or not auth_header.startswith("Bearer "):
        return error_response(message="Missing token", code="UNAUTHORIZED"), status.HTTP_401_UNAUTHORIZED
    token = auth_header.split(" ")[1]
    current_user = get_current_user_from_token(db, token)
    return success_response(data=current_user)


@router.post("/change-password")
def change_user_password(
    payload: ChangePasswordRequest,
    request: Request,
    db: Session = Depends(get_db),
):
    auth_header = request.headers.get("Authorization")
    if not auth_header or not auth_header.startswith("Bearer "):
        return error_response(message="Missing token", code="UNAUTHORIZED"), status.HTTP_401_UNAUTHORIZED
    token = auth_header.split(" ")[1]
    current_user = get_current_user_from_token(db, token)
    result = change_password(
        db=db,
        user=current_user,
        old_password=payload.old_password,
        new_password=payload.new_password,
    )
    return success_response(data=result, message="Password changed successfully.")