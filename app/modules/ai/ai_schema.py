# app/modules/ai/ai_schema.py

from typing import List, Optional
from pydantic import BaseModel, Field


# ── Chatbot ───────────────────────────────────────────────────────────────────
class ChatMessage(BaseModel):
    role: str = Field(..., description="'user' ou 'assistant'")
    content: str


class ChatRequest(BaseModel):
    user_id: int
    message: str
    history: List[ChatMessage] = []


class ChatResponse(BaseModel):
    reply: str
    history: List[ChatMessage]


# ── Lettre de motivation ──────────────────────────────────────────────────────
class LetterRequest(BaseModel):
    user_id: int
    job_id: int
    tone: Optional[str] = Field(
        "professional",
        description="Ton : professional, enthusiastic, formal"
    )


class LetterResponse(BaseModel):
    letter: str
    job_title: str
    company: str


# ── Roadmap de formation ──────────────────────────────────────────────────────
class RoadmapRequest(BaseModel):
    user_id: int
    job_id: int


class RoadmapStep(BaseModel):
    step: int
    skill: str
    resources: List[str]
    estimated_weeks: int


class RoadmapResponse(BaseModel):
    user_id: int
    job_id: int
    job_title: str
    missing_skills: List[str]
    roadmap: List[RoadmapStep]
    total_weeks: int


# ── Simulateur d'entretien ────────────────────────────────────────────────────
class InterviewRequest(BaseModel):
    user_id: int
    job_id: int
    num_questions: int = Field(5, ge=1, le=10)


class InterviewQuestion(BaseModel):
    question_number: int
    question: str
    category: str


class InterviewResponse(BaseModel):
    job_title: str
    company: str
    questions: List[InterviewQuestion]


# ── Détection de fraude ───────────────────────────────────────────────────────
class FraudCheckRequest(BaseModel):
    job_id: int


class FraudCheckResponse(BaseModel):
    job_id: int
    job_title: str
    is_suspicious: bool
    risk_level: str
    flags: List[str]
    recommendation: str