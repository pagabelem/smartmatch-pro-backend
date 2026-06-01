"""
main.py — FastAPI application entry point.

Run with:
    uvicorn app.main:app --reload

Swagger UI:    http://localhost:8000/docs
ReDoc:         http://localhost:8000/redoc
OpenAPI JSON:  http://localhost:8000/openapi.json
"""

from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import JSONResponse, RedirectResponse

from app.config import settings
from app.database import check_db_connection
from app.core.exceptions import (
    AppException,
    app_exception_handler,
    unhandled_exception_handler,
)

# ── Import all models ─────────────────────────────────────────────────────────
from app.modules.users.user_model import Profile, User                      # noqa: F401
from app.modules.auth.auth_model import RefreshToken                        # noqa: F401
from app.modules.skills.skill_model import Skill                            # noqa: F401
from app.modules.resumes.resume_model import Resume                         # noqa: F401
from app.modules.jobs.job_model import Job                                  # noqa: F401
from app.modules.imports.import_model import Import                         # noqa: F401
from app.modules.favorites.favorite_model import Favorite                   # noqa: F401
from app.modules.matching.recommendation_model import Recommendation        # noqa: F401
from app.modules.skill_gap.skill_gap_model import SkillGap                  # noqa: F401

# ── Import all routers ────────────────────────────────────────────────────────
from app.modules.auth.auth_router import router as auth_router
from app.modules.skills.skill_router import router as skills_router
from app.modules.users.user_router import router as users_router
from app.modules.profiles.profile_router import router as profiles_router
from app.modules.resumes.resume_router import router as resumes_router
from app.modules.nlp.nlp_router import router as nlp_router
from app.modules.storage.storage_router import router as storage_router
from app.modules.jobs.job_router import router as jobs_router
from app.modules.imports.import_router import router as imports_router
from app.modules.favorites.favorite_router import router as favorites_router
from app.modules.matching.matching_router import router as matching_router
from app.modules.skill_gap.skill_gap_router import router as skill_gap_router

# ── NLP preload ───────────────────────────────────────────────────────────────
from app.modules.nlp.nlp_service import preload_nlp_model

API_PREFIX = "/api/v1"


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    # ── Startup ───────────────────────────────────────────────────────────────
    print(f"🚀  Starting {settings.APP_NAME} v{settings.APP_VERSION}")
    print(f"    Environment : {settings.ENVIRONMENT}")
    print(f"    Database    : {settings.DATABASE_URL}")
    print(f"    Debug mode  : {settings.DEBUG}")
    if not check_db_connection():
        raise RuntimeError(
            f"Cannot connect to database: {settings.DATABASE_URL}\n"
            "Run 'alembic upgrade head' to create the tables."
        )
    print("    Database    : ✓ connection OK")

    preload_nlp_model()

    yield

    # ── Shutdown ──────────────────────────────────────────────────────────────
    print(f"🛑  Shutting down {settings.APP_NAME}")


def create_app() -> FastAPI:
    app = FastAPI(
        title=settings.APP_NAME,
        version=settings.APP_VERSION,
        description=(
            "**SmartMatch Pro** — Intelligent Job Recommendation & Career Assistant.\n\n"
            "Authenticate via `/api/v1/auth/login` to get a JWT bearer token, "
            "then click **Authorize** to access protected endpoints."
        ),
        lifespan=lifespan,
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/openapi.json",
    )

    # ── Middlewares ────────────────────────────────────────────────────────────
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.allowed_origins_list,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    if settings.ENVIRONMENT == "production":
        app.add_middleware(
            TrustedHostMiddleware,
            allowed_hosts=["yourdomain.com", "www.yourdomain.com"],
        )

    # ── Exception handlers ────────────────────────────────────────────────────
    app.add_exception_handler(AppException, app_exception_handler)
    app.add_exception_handler(Exception, unhandled_exception_handler)

    # ── Routers Membre 1 ──────────────────────────────────────────────────────
    app.include_router(auth_router,      prefix=API_PREFIX, tags=["Authentication"])
    app.include_router(skills_router,    prefix=API_PREFIX, tags=["Skills"])
    app.include_router(users_router,     prefix=API_PREFIX, tags=["Users"])
    app.include_router(profiles_router,  prefix=API_PREFIX, tags=["Profiles"])
    app.include_router(resumes_router,   prefix=API_PREFIX, tags=["Resumes"])
    app.include_router(nlp_router,       prefix=API_PREFIX, tags=["NLP"])
    app.include_router(storage_router,   prefix=API_PREFIX, tags=["Storage"])

    # ── Routers Membre 2 ──────────────────────────────────────────────────────
    app.include_router(jobs_router,       prefix=API_PREFIX, tags=["Jobs"])
    app.include_router(imports_router,    prefix=API_PREFIX, tags=["Imports"])
    app.include_router(favorites_router,  prefix=API_PREFIX, tags=["Favorites"])
    app.include_router(matching_router,   prefix=API_PREFIX, tags=["Matching"])
    app.include_router(skill_gap_router,  prefix=API_PREFIX, tags=["Skill Gap"])

    return app


app = create_app()


# ── Health check ──────────────────────────────────────────────────────────────
@app.get(
    "/health",
    tags=["System"],
    summary="Health check",
    description="Returns the operational status of the API and its dependencies.",
)
def health_check() -> JSONResponse:
    db_ok = check_db_connection()
    payload = {
        "status":      "healthy" if db_ok else "degraded",
        "app":         settings.APP_NAME,
        "version":     settings.APP_VERSION,
        "environment": settings.ENVIRONMENT,
        "database":    "connected" if db_ok else "unreachable",
    }
    return JSONResponse(content=payload, status_code=200 if db_ok else 503)


@app.get("/", include_in_schema=False)
def root():
    return RedirectResponse(url="/docs")