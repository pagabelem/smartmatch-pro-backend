"""
config.py — Centralized application settings via pydantic-settings v2.

All values are read from environment variables or the .env file.
Import the singleton `settings` everywhere — never instantiate Settings directly.

PostgreSQL connection
---------------------
Two ways to configure the database (in your .env):

  Option A — full URL (recommended for managed DBs like Railway, Supabase, Render):
      DATABASE_URL=postgresql+psycopg2://user:password@host:5432/dbname

  Option B — individual fields (auto-assembled into a URL at startup):
      POSTGRES_HOST=localhost
      POSTGRES_PORT=5432
      POSTGRES_USER=smartmatch
      POSTGRES_PASSWORD=mypassword
      POSTGRES_DB=smartmatch_db

If DATABASE_URL is set, it takes priority over the individual fields.
"""

from functools import lru_cache

from pydantic import field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # ── Application ───────────────────────────────────────────────────────────
    APP_NAME: str = "SmartMatch Pro"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = False
    ENVIRONMENT: str = "development"   # development | staging | production

    # ── Database — PostgreSQL ─────────────────────────────────────────────────
    # Option A: full URL (takes priority if provided)
    DATABASE_URL: str = ""

    # Option B: individual fields (assembled into DATABASE_URL by model_validator)
    POSTGRES_HOST: str = "localhost"
    POSTGRES_PORT: int = 5432
    POSTGRES_USER: str = "smartmatch"
    POSTGRES_PASSWORD: str = "smartmatch"
    POSTGRES_DB: str = "smartmatch_db"

    # Connection pool (psycopg2 / SQLAlchemy QueuePool)
    DB_POOL_SIZE: int = 5        # persistent connections kept open
    DB_MAX_OVERFLOW: int = 10    # extra connections allowed under peak load
    DB_POOL_TIMEOUT: int = 30    # seconds to wait before "pool exhausted" error
    DB_POOL_RECYCLE: int = 1800  # recycle connections every 30 min (avoids timeouts)

    # ── JWT ───────────────────────────────────────────────────────────────────
    SECRET_KEY: str = "CHANGE_ME_IN_PRODUCTION_USE_openssl_rand_hex_32"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # ── CORS ──────────────────────────────────────────────────────────────────
    ALLOWED_ORIGINS: str = "http://localhost:3000,http://127.0.0.1:3000"

    # ── File storage ──────────────────────────────────────────────────────────
    UPLOAD_DIR: str = "app/storage/uploads"
    MAX_FILE_SIZE_MB: int = 5
    ALLOWED_RESUME_EXTENSIONS: str = "pdf,docx"

    # ── NLP ───────────────────────────────────────────────────────────────────
    SPACY_MODEL_FR: str = "fr_core_news_md"
    SPACY_MODEL_EN: str = "en_core_web_md"

    # ── OpenAI (optional — AI modules V2/V3) ─────────────────────────────────
    OPENAI_API_KEY: str = ""
    OPENAI_MODEL: str = "gpt-4o-mini"

    # ── Pagination ────────────────────────────────────────────────────────────
    DEFAULT_PAGE_SIZE: int = 20
    MAX_PAGE_SIZE: int = 100

    # ── Pydantic-settings config ──────────────────────────────────────────────
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )

    # ── Assemble DATABASE_URL from individual fields if not provided ──────────
    @model_validator(mode="after")
    def assemble_database_url(self) -> "Settings":
        """
        Build DATABASE_URL from POSTGRES_* fields when DATABASE_URL is empty.
        Also normalises bare 'postgresql://' and 'postgres://' (Heroku/Railway)
        to the explicit 'postgresql+psycopg2://' driver string that SQLAlchemy needs.
        """
        if not self.DATABASE_URL:
            self.DATABASE_URL = (
                f"postgresql+psycopg2://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}"
                f"@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"
            )
        else:
            url = self.DATABASE_URL
            if url.startswith("postgres://"):
                self.DATABASE_URL = url.replace("postgres://", "postgresql+psycopg2://", 1)
            elif url.startswith("postgresql://") and "+psycopg2" not in url:
                self.DATABASE_URL = url.replace("postgresql://", "postgresql+psycopg2://", 1)
        return self

    @model_validator(mode="after")
    def reject_insecure_in_production(self) -> "Settings":
        if self.ENVIRONMENT == "production":
            if self.SECRET_KEY == "CHANGE_ME_IN_PRODUCTION_USE_openssl_rand_hex_32":
                raise ValueError(
                    "SECRET_KEY must be changed before running in production. "
                    "Generate one with:  openssl rand -hex 32"
                )
        return self

    @field_validator("SECRET_KEY")
    @classmethod
    def warn_default_secret_key(cls, v: str) -> str:
        if v == "CHANGE_ME_IN_PRODUCTION_USE_openssl_rand_hex_32":
            import warnings
            warnings.warn(
                "SECRET_KEY is using the default insecure value. "
                "Run: openssl rand -hex 32  and set it in your .env file.",
                stacklevel=2,
            )
        return v

    # ── Derived properties ────────────────────────────────────────────────────
    @property
    def allowed_origins_list(self) -> list[str]:
        return [o.strip() for o in self.ALLOWED_ORIGINS.split(",") if o.strip()]

    @property
    def allowed_resume_extensions_set(self) -> set[str]:
        return {ext.strip().lower() for ext in self.ALLOWED_RESUME_EXTENSIONS.split(",")}

    @property
    def max_file_size_bytes(self) -> int:
        return self.MAX_FILE_SIZE_MB * 1024 * 1024


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()


settings: Settings = get_settings()