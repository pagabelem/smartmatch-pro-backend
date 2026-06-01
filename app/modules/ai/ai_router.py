# app/modules/ai/ai_router.py

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.responses import ok
from app.dependencies import get_db, get_current_active_user
from app.modules.ai.ai_schema import (
    ChatRequest,
    ChatResponse,
    FraudCheckRequest,
    FraudCheckResponse,
    InterviewRequest,
    InterviewResponse,
    LetterRequest,
    LetterResponse,
    RoadmapRequest,
    RoadmapResponse,
)
from app.modules.ai.ai_service import AIService
from app.modules.users.user_model import User

router = APIRouter(prefix="/ai", tags=["IA — Intelligence Artificielle"])


@router.post(
    "/chat",
    status_code=status.HTTP_200_OK,
    summary="Chatbot assistant carrière",
)
def chat(
    payload: ChatRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Chatbot contextuel basé sur le profil et les offres."""
    if current_user.id != payload.user_id and not current_user.is_superuser:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Accès non autorisé.",
        )
    result = AIService.chat(
        db, payload.user_id, payload.message, payload.history
    )
    return ok(
        data=ChatResponse(**result).model_dump(mode="json"),
        message="Réponse générée.",
    )


@router.post(
    "/letter",
    status_code=status.HTTP_200_OK,
    summary="Générer une lettre de motivation",
)
def generate_letter(
    payload: LetterRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Génère une lettre de motivation personnalisée."""
    if current_user.id != payload.user_id and not current_user.is_superuser:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Accès non autorisé.",
        )
    try:
        result = AIService.generate_letter(
            db, payload.user_id, payload.job_id, payload.tone
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)
        )
    return ok(
        data=LetterResponse(**result).model_dump(mode="json"),
        message="Lettre de motivation générée.",
    )


@router.post(
    "/roadmap",
    status_code=status.HTTP_200_OK,
    summary="Générer un plan de formation",
)
def generate_roadmap(
    payload: RoadmapRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Génère un roadmap de formation basé sur les skills manquantes."""
    if current_user.id != payload.user_id and not current_user.is_superuser:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Accès non autorisé.",
        )
    try:
        result = AIService.generate_roadmap(
            db, payload.user_id, payload.job_id
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)
        )
    return ok(
        data=RoadmapResponse(**result).model_dump(mode="json"),
        message="Roadmap de formation généré.",
    )


@router.post(
    "/interview",
    status_code=status.HTTP_200_OK,
    summary="Simuler un entretien d'embauche",
)
def generate_interview(
    payload: InterviewRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Génère des questions d'entretien adaptées au poste."""
    if current_user.id != payload.user_id and not current_user.is_superuser:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Accès non autorisé.",
        )
    try:
        result = AIService.generate_interview(
            db, payload.user_id, payload.job_id, payload.num_questions
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)
        )
    return ok(
        data=InterviewResponse(**result).model_dump(mode="json"),
        message="Questions d'entretien générées.",
    )


@router.post(
    "/fraud-check",
    status_code=status.HTTP_200_OK,
    summary="Vérifier si une offre est suspecte",
)
def check_fraud(
    payload: FraudCheckRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Analyse une offre pour détecter des indicateurs de fraude."""
    try:
        result = AIService.check_fraud(db, payload.job_id)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)
        )
    return ok(
        data=FraudCheckResponse(**result).model_dump(mode="json"),
        message=result["recommendation"],
    )