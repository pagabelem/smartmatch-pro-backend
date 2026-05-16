"""
core/constants.py — Application-wide immutable constants.

Rules
-----
- Only true constants here (never change at runtime).
- Config values that depend on the environment belong in config.py.
- Business rules that may evolve belong in shared/enums.py or the domain module.
"""

# ── API ───────────────────────────────────────────────────────────────────────
API_V1_PREFIX = "/api/v1"
API_TITLE      = "SmartMatch Pro API"
API_DESCRIPTION = (
    "Intelligent Job Recommendation & Career Assistant.\n\n"
    "Authenticate via `POST /api/v1/auth/login` to obtain a JWT bearer token."
)

# ── JWT ───────────────────────────────────────────────────────────────────────
JWT_TOKEN_TYPE    = "Bearer"
JWT_HEADER_NAME   = "Authorization"
JWT_HEADER_PREFIX = "Bearer "

# ── Pagination defaults ───────────────────────────────────────────────────────
DEFAULT_PAGE      = 1
DEFAULT_PAGE_SIZE = 20
MAX_PAGE_SIZE     = 100

# ── File uploads ──────────────────────────────────────────────────────────────
ALLOWED_CV_EXTENSIONS   = {"pdf", "docx"}
ALLOWED_IMAGE_EXTENSIONS = {"png", "jpg", "jpeg", "webp"}
MAX_CV_SIZE_MB           = 5
MAX_IMAGE_SIZE_MB        = 2
CV_UPLOAD_SUBDIR         = "resumes"
IMAGE_UPLOAD_SUBDIR      = "avatars"
DATASET_UPLOAD_SUBDIR    = "datasets"

# ── NLP ───────────────────────────────────────────────────────────────────────
SUPPORTED_LANGUAGES       = {"fr", "en"}
DEFAULT_LANGUAGE           = "fr"
MIN_SKILL_CONFIDENCE       = 0.70   # minimum NER confidence to accept a skill
SKILLS_TAXONOMY_PATH       = "datasets/skills_taxonomy.csv"
HARD_SKILLS_DICT_FR        = "app/modules/nlp/dictionaries/hard_skills_fr.json"
HARD_SKILLS_DICT_EN        = "app/modules/nlp/dictionaries/hard_skills_en.json"
SOFT_SKILLS_DICT_FR        = "app/modules/nlp/dictionaries/soft_skills_fr.json"
SOFT_SKILLS_DICT_EN        = "app/modules/nlp/dictionaries/soft_skills_en.json"

# ── Matching ──────────────────────────────────────────────────────────────────
MIN_MATCH_SCORE           = 0.0    # 0 % — include all results by default
DEFAULT_TOP_N_RESULTS      = 10    # number of recommendations to return
MAX_TOP_N_RESULTS          = 50

# ── Skill gap ─────────────────────────────────────────────────────────────────
MAX_SKILL_GAP_SUGGESTIONS  = 10   # max missing skills shown per offer

# ── Dashboard ─────────────────────────────────────────────────────────────────
TOP_SKILLS_CHART_LIMIT     = 10   # "Top N skills" bar chart
SCRAPING_SCHEDULE_CRON     = "0 2 1 * *"  # 02:00 on the 1st of every month

# ── Security ──────────────────────────────────────────────────────────────────
PASSWORD_MIN_LENGTH        = 8
PASSWORD_MAX_LENGTH        = 128
MAX_LOGIN_ATTEMPTS         = 5     # lockout after N failures (Phase 2+)
LOCKOUT_DURATION_MINUTES   = 15

# ── HTTP headers ──────────────────────────────────────────────────────────────
CONTENT_TYPE_JSON = "application/json"
CONTENT_TYPE_PDF  = "application/pdf"
CONTENT_TYPE_DOCX = (
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
)