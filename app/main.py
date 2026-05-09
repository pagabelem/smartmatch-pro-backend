"""
main.py — FastAPI application entry point.

Run with:
    uvicorn app.main:app --reload

Swagger UI:    http://localhost:8000/docs
ReDoc:         http://localhost:8000/redoc
OpenAPI JSON: http://localhost:8000/openapi.json
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

# ── Import all models so Alembic / create_all_tables() can see them ───────────
from app.modules.users.user_model import Profile, User      # noqa: F401
from app.modules.auth.auth_model import RefreshToken        # noqa: F401
from app.modules.skills.skill_model import Skill            # noqa: F401

# ── Import routers ────────────────────────────────────────────────────────────
# Phase 1 routers
from app.modules.auth.auth_router import router as auth_router
from app.modules.skills.skill_router import router as skills_router

# Routers des phases suivantes (à décommenter au fur et à mesure)
# from app.modules.users.user_router import router as users_router       # Phase 2
# from app.modules.profiles.profile_router import router as profiles_router # Phase 3
# from app.modules.resumes.resume_router import router as resumes_router   # Phase 4
# from app.modules.nlp.nlp_router import router as nlp_router            # Phase 5
# from app.modules.matching.matching_router import router as matching_router # Phase 6

API_PREFIX = "/api/v1"


# ── Lifespan (startup / shutdown hooks) ───────────────────────────────────────
@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """
    Code before `yield` runs at startup.
    Code after  `yield` runs at shutdown.
    """
    # ── Startup ───────────────────────────────────────────────────────────────
    print(f"🚀  Starting {settings.APP_NAME} v{settings.APP_VERSION}")
    print(f"    Environment : {settings.ENVIRONMENT}")
    print(f"    Database    : {settings.DATABASE_URL}")
    print(f"    Debug mode  : {settings.DEBUG}")

    # Verify DB is reachable before accepting traffic
    if not check_db_connection():
        raise RuntimeError(
            f"Cannot connect to database: {settings.DATABASE_URL}\n"
            "Run 'alembic upgrade head' to create the tables."
        )
    print("    Database    : ✓ connection OK")

    yield  # ← application is running

    # ── Shutdown ──────────────────────────────────────────────────────────────
    print(f"🛑  Shutting down {settings.APP_NAME}")


# ── App factory ───────────────────────────────────────────────────────────────
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

    # CORS
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.allowed_origins_list,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Trusted Host (Production)
    if settings.ENVIRONMENT == "production":
        app.add_middleware(
            TrustedHostMiddleware,
            allowed_hosts=["yourdomain.com", "www.yourdomain.com"],
        )

    # ── Exception handlers ────────────────────────────────────────────────
    app.add_exception_handler(AppException, app_exception_handler)
    app.add_exception_handler(Exception, unhandled_exception_handler)

    # ── Routers ───────────────────────────────────────────────────────────────
    
    # Phase 1: Authentication & Skills
    app.include_router(auth_router, prefix=f"{API_PREFIX}/auth", tags=["Authentication"])
    app.include_router(skills_router, prefix=f"{API_PREFIX}", tags=["Skills"])
    
    # Phase 2+ (Un-comment as you implement)
    # app.include_router(users_router, prefix=f"{API_PREFIX}/users", tags=["Users"])

    return app


# ── Application instance ──────────────────────────────────────────────────────
app = create_app()


# ── Health check ──────────────────────────────────────────────────────────────
@app.get(
    "/health",
    tags=["System"],
    summary="Health check",
    description="Returns the operational status of the API and its dependencies.",
    response_description="Service status payload.",
)
def health_check() -> JSONResponse:
    db_ok = check_db_connection()

    payload = {
        "status": "healthy" if db_ok else "degraded",
        "app": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "environment": settings.ENVIRONMENT,
        "database": "connected" if db_ok else "unreachable",
    }

    status_code = 200 if db_ok else 503
    return JSONResponse(content=payload, status_code=status_code)


# ── Root redirect ─────────────────────────────────────────────────────────────
@app.get("/", include_in_schema=False)
def root():
    """Redirect browsers hitting the root URL to the API docs."""
    return RedirectResponse(url="/docs")