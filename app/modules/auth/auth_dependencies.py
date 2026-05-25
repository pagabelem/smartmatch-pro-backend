# app/modules/auth/auth_dependencies.py

from fastapi import Depends
from sqlalchemy.orm import Session

from app.dependencies import get_db
from app.modules.auth.auth_service import get_current_user_from_token


def get_current_user(db: Session = Depends(get_db), token: str = Depends(get_token)):
    return get_current_user_from_token(db, token)


def get_token(authorization: str = None):
    # Logique pour extraire le token du header Authorization
    pass