# app/config.py - version finale sans import circulaire

from functools import lru_cache
from pydantic import field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    APP_NAME: str = "SmartMatch Pro"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = False
    ENVIRONMENT: str = "development"

    DATABASE_URL: str = ""

    POSTGRES_HOST: str = "localhost"
    POSTGRES_PORT: int = 5432
    POSTGRES_USER: str = "smartmatch"
    POSTGRES_PASSWORD: str = "smartmatch"
    POSTGRES_DB: str = "smartmatch_db"

    DB_POOL_SIZE: int = 5
    DB_MAX_OVERFLOW: int = 10
    DB_POOL_TIMEOUT: int = 30
    DB_POOL_RECYCLE: int = 1800

    SECRET_KEY: str = "CHANGE_ME_IN_PRODUCTION_USE_openssl_rand_hex_32"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    ALLOWED_ORIGINS: str = "http://localhost:3000,http://127.0.0.1:3000"

    # ✅ CORRIGÉ : UPLOAD_DIR modifié
    UPLOAD_DIR: str = "app/storage"
    # ✅ AJOUTÉ : STORAGE_DIR pour le module storage
    STORAGE_DIR: str = "app/storage"
    MAX_FILE_SIZE_MB: int = 5
    ALLOWED_RESUME_EXTENSIONS: str = "pdf,docx"

    SPACY_MODEL_FR: str = "fr_core_news_md"
    SPACY_MODEL_EN: str = "en_core_web_md"

    OPENAI_API_KEY: str = ""
    OPENAI_MODEL: str = "gpt-4o-mini"

    DEFAULT_PAGE_SIZE: int = 20
    MAX_PAGE_SIZE: int = 100

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )

    @model_validator(mode="after")
    def assemble_database_url(self) -> "Settings":
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
                raise ValueError("SECRET_KEY must be changed before running in production.")
        return self

    @field_validator("SECRET_KEY")
    @classmethod
    def warn_default_secret_key(cls, v: str) -> str:
        if v == "CHANGE_ME_IN_PRODUCTION_USE_openssl_rand_hex_32":
            import warnings
            warnings.warn("SECRET_KEY is using the default insecure value.", stacklevel=2)
        return v

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

# AUCUN IMPORT DE DATABASE ICI