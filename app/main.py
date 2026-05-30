# app/main.py

from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import JSONResponse

from app.config import settings
from app.database import check_db_connection

# ── Import tous les modèles ────────────────────────────────────────────────────
from app.modules.users.user_model     import Profile, User      # noqa: F401
from app.modules.skills.skill_model   import Skill              # noqa: F401
from app.modules.jobs.job_model       import Job                # noqa: F401
from app.modules.imports.import_model import Import             # noqa: F401
from app.modules.favorites.favorite_model import Favorite       # noqa: F401

# ── Import des routers ────────────────────────────────────────────────────────
# from app.modules.auth.auth_router        import router as auth_router
# from app.modules.users.user_router       import router as users_router
# from app.modules.profiles.profile_router import router as profiles_router
# from app.modules.resumes.resume_router   import router as resumes_router
# from app.modules.nlp.nlp_router          import router as nlp_router

from app.modules.skills.skill_router     import router as skills_router
from app.modules.jobs.job_router         import router as jobs_router
from app.modules.imports.import_router   import router as imports_router
from app.modules.favorites.favorite_router import router as favorites_router

# from app.modules.matching.matching_router   import router as matching_router
# from app.modules.skill_gap.skill_gap_router import router as skill_gap_router
# from app.modules.dashboard.dashboard_router import router as dashboard_router
# from app.modules.ai.ai_router               import router as ai_router

API_PREFIX = "/api/v1"


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
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
    yield
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

    # ── Routers ────────────────────────────────────────────────────────────────
    app.include_router(skills_router,    prefix=API_PREFIX)
    app.include_router(jobs_router,      prefix=API_PREFIX)
    app.include_router(imports_router,   prefix=API_PREFIX)
    app.include_router(favorites_router, prefix=API_PREFIX)

    # app.include_router(matching_router,  prefix=API_PREFIX)
    # app.include_router(skill_gap_router, prefix=API_PREFIX)
    # app.include_router(dashboard_router, prefix=API_PREFIX)
    # app.include_router(ai_router,        prefix=API_PREFIX)

    return app


app = create_app()


@app.get("/health", tags=["System"], summary="Health check")
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
    from fastapi.responses import RedirectResponse
    return RedirectResponse(url="/docs")