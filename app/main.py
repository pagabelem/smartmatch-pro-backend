from fastapi import FastAPI

app = FastAPI(
    title="SmartMatch Pro API",
    description="Backend intelligent pour analyse d'offres, matching et recommandation",
    version="1.0.0"
)

@app.get("/")
def root():
    return {
        "message": "SmartMatch Pro Backend is running"
    }

@app.get("/health")
def health_check():
    return {
        "status": "ok"
    }

"""
main.py — FastAPI application entry point.

Run with:
    uvicorn app.main:app --reload

Swagger UI:  http://localhost:8000/docs
ReDoc:       http://localhost:8000/redoc
OpenAPI JSON: http://localhost:8000/openapi.json
"""

from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import JSONResponse

from app.config import settings
from app.database import check_db_connection

# ── Import all models so Alembic / create_all_tables() can see them ───────────
# Even if models are not used directly here, the import registers them on
# Base.metadata — required for Alembic autogenerate to work.
from app.modules.users.user_model import Profile, User  # noqa: F401

# ── Import routers ────────────────────────────────────────────────────────────
# Phase 0: only the health router is active.
# Un-comment each router as you complete the corresponding phase.

# from app.modules.auth.auth_router     import router as auth_router       # Phase 1
# from app.modules.users.user_router    import router as users_router      # Phase 2
# from app.modules.profiles.profile_router import router as profiles_router # Phase 3
# from app.modules.resumes.resume_router import router as resumes_router   # Phase 4
# from app.modules.nlp.nlp_router       import router as nlp_router        # Phase 5
# from app.modules.matching.matching_router import router as matching_router # Phase 6 (Membre 2)
# from app.modules.skill_gap.skill_gap_router import router as skill_gap_router
# from app.modules.favorites.favorite_router import router as favorites_router
# from app.modules.dashboard.dashboard_router import router as dashboard_router
# from app.modules.ai.ai_router         import router as ai_router          # Phase V2

API_PREFIX = "/api/v1"


# ── Lifespan (startup / shutdown hooks) ───────────────────────────────────────
@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """
    Code before `yield` runs at startup.
    Code after  `yield` runs at shutdown.

    Add expensive initializations here (NLP model loading, connection pools, etc.)
    so they happen once, not on every request.
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

    # Phase 5: pre-load spaCy models here to avoid loading on first request
    # from app.modules.nlp.nlp_service import nlp_service
    # nlp_service.load_models()
    # print("    spaCy       : ✓ models loaded")

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
        # Hide docs in production
        # docs_url=None if settings.ENVIRONMENT == "production" else "/docs",
    )

    # ── Middlewares ────────────────────────────────────────────────────────────

    # CORS — allow the frontend (Next.js) to call the API
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.allowed_origins_list,
        allow_credentials=True,            # required for cookies / auth headers
        allow_methods=["*"],               # GET, POST, PUT, DELETE, OPTIONS, PATCH
        allow_headers=["*"],               # Authorization, Content-Type, etc.
    )

    # Trusted Host — prevent HTTP Host header attacks in production
    if settings.ENVIRONMENT == "production":
        app.add_middleware(
            TrustedHostMiddleware,
            allowed_hosts=["yourdomain.com", "www.yourdomain.com"],
        )

    # ── Routers ───────────────────────────────────────────────────────────────
    # Each router is registered with a versioned prefix and a tag for Swagger grouping.
    # Un-comment as you implement each phase:

    # app.include_router(auth_router,      prefix=f"{API_PREFIX}/auth",         tags=["Authentication"])
    # app.include_router(users_router,     prefix=f"{API_PREFIX}/users",        tags=["Users"])
    # app.include_router(profiles_router,  prefix=f"{API_PREFIX}/profiles",     tags=["Profiles"])
    # app.include_router(resumes_router,   prefix=f"{API_PREFIX}/resumes",      tags=["Resumes"])
    # app.include_router(nlp_router,       prefix=f"{API_PREFIX}/nlp",          tags=["NLP"])
    # app.include_router(matching_router,  prefix=f"{API_PREFIX}/matching",     tags=["Matching"])
    # app.include_router(skill_gap_router, prefix=f"{API_PREFIX}/skill-gap",    tags=["Skill Gap"])
    # app.include_router(favorites_router, prefix=f"{API_PREFIX}/favorites",    tags=["Favorites"])
    # app.include_router(dashboard_router, prefix=f"{API_PREFIX}/dashboard",    tags=["Dashboard"])
    # app.include_router(ai_router,        prefix=f"{API_PREFIX}/ai",           tags=["AI Services"])

    return app


# ── Application instance ──────────────────────────────────────────────────────
app = create_app()


# ── Health check ──────────────────────────────────────────────────────────────
@app.get(
    "/health",
    tags=["System"],
    summary="Health check",
    description=(
        "Returns the operational status of the API and its dependencies. "
        "Use this endpoint for load-balancer health checks."
    ),
    response_description="Service status payload.",
)
def health_check() -> JSONResponse:
    """
    Returns HTTP 200 if everything is healthy, HTTP 503 otherwise.

    Example response:
        {
          "status": "healthy",
          "app": "SmartMatch Pro",
          "version": "1.0.0",
          "environment": "development",
          "database": "connected"
        }
    """
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
    from fastapi.responses import RedirectResponse
    return RedirectResponse(url="/docs")