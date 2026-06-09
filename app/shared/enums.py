# app/shared/enums.py

"""
shared/enums.py — All application-level enumerations.

Why enums?
----------
Using raw strings like "CDI" or "active" across the codebase leads to typos
and makes refactoring dangerous. Enums give you:
  - Auto-completion in your IDE.
  - A single place to add/rename values.
  - Automatic validation in Pydantic schemas (pass the enum class as the type).

Usage
-----
  # In a Pydantic schema:
  from app.shared.enums import ContractType
  class JobCreateSchema(BaseModel):
      contract_type: ContractType

  # In a SQLAlchemy model (stores the .value string in the DB column):
  from sqlalchemy import Enum as SAEnum
  contract_type: Mapped[str] = mapped_column(SAEnum(ContractType, values_callable=lambda e: [i.value for i in e]))

  # Comparison:
  if job.contract_type == ContractType.CDI:
      ...
"""

from enum import Enum


# ── User & Auth ───────────────────────────────────────────────────────────────
class UserRole(str, Enum):
    """Role assigned to a user account."""
    STUDENT   = "student"    # default for all registered users
    ADMIN     = "admin"      # full back-office access
    MODERATOR = "moderator"  # can manage jobs/skills, no user management


class AccountStatus(str, Enum):
    """Lifecycle state of a user account."""
    ACTIVE    = "active"
    INACTIVE  = "inactive"   # disabled by admin
    PENDING   = "pending"    # email not yet verified (V2)
    BANNED    = "banned"


# ── Profile & Education ───────────────────────────────────────────────────────
class ProfileStatus(str, Enum):
    """Profile completion status."""
    DRAFT = "draft"
    COMPLETED = "completed"
    VERIFIED = "verified"


class EducationLevel(str, Enum):
    """Education level options."""
    BACHELOR = "bachelor"
    MASTER = "master"
    PHD = "phd"
    ENGINEERING = "engineering"
    OTHER = "other"


# ── Job offers ────────────────────────────────────────────────────────────────
class ContractType(str, Enum):
    """Type of employment contract."""
    CDI         = "CDI"          # Permanent contract
    CDD         = "CDD"          # Fixed-term contract
    STAGE       = "Stage"        # Internship
    ALTERNANCE  = "Alternance"   # Work-study / apprenticeship
    FREELANCE   = "Freelance"
    PART_TIME   = "Part-time"
    VOLUNTEER   = "Volunteer"
    OTHER       = "Other"


class JobStatus(str, Enum):
    """Publication status of a job offer in our database."""
    ACTIVE    = "active"     # visible to students
    EXPIRED   = "expired"    # past closing date
    SUSPENDED = "suspended"  # hidden by admin (suspected fraud, etc.)
    DRAFT     = "draft"      # imported but not yet validated


class ExperienceLevel(str, Enum):
    """Required seniority level for a job offer."""
    JUNIOR     = "junior"     # 0–2 years
    MID        = "mid"        # 2–5 years
    SENIOR     = "senior"     # 5–10 years
    LEAD       = "lead"       # 10+ / team lead
    INTERNSHIP = "internship" # no experience required
    ANY        = "any"        # not specified


class WorkMode(str, Enum):
    """Where the work is performed."""
    ON_SITE  = "on_site"
    REMOTE   = "remote"
    HYBRID   = "hybrid"
    ANY      = "any"


class DegreeLevel(str, Enum):
    """Required educational level for a job offer."""
    BAC_2 = "Bac+2"
    BAC_3 = "Bac+3"
    BAC_5 = "Bac+5"
    ANY   = "any"


# ── Skills ────────────────────────────────────────────────────────────────────
class SkillType(str, Enum):
    """Broad category of a skill."""
    HARD = "hard"   # technical, measurable (Python, SQL, TensorFlow…)
    SOFT = "soft"   # interpersonal, behavioural (communication, leadership…)


class SkillCategory(str, Enum):
    """
    Sub-domain of a hard skill — used by the treemap / dashboard visualisation.
    """
    PROGRAMMING  = "programming"
    AI_ML        = "ai_ml"
    NLP          = "nlp"
    WEB_FRONTEND = "web_frontend"
    WEB_BACKEND  = "web_backend"
    BIG_DATA     = "big_data"
    DATABASE     = "database"
    DEVOPS       = "devops"
    DATA_VIZ     = "data_viz"
    SECURITY     = "security"
    MANAGEMENT   = "management"
    SOFT_SKILL   = "soft_skill"
    OTHER        = "other"


# ── NLP & Language ────────────────────────────────────────────────────────────
class Language(str, Enum):
    """Languages supported by the NLP pipeline in V1."""
    FRENCH  = "fr"
    ENGLISH = "en"
    UNKNOWN = "unknown"


# ── Import / Data sources ─────────────────────────────────────────────────────
class ImportSource(str, Enum):
    """Origin of a job-offer dataset."""
    CSV          = "csv"
    JSON         = "json"
    SCRAPER_REKRUTE    = "scraper_rekrute"
    SCRAPER_EMPLOI     = "scraper_emploidiali"
    SCRAPER_INDEED     = "scraper_indeed"
    SCRAPER_LINKEDIN   = "scraper_linkedin"
    MANUAL       = "manual"


class ImportStatus(str, Enum):
    """Processing state of a data import job."""
    PENDING    = "pending"
    PROCESSING = "processing"
    DONE       = "done"
    FAILED     = "failed"


# ── Salary ────────────────────────────────────────────────────────────────────
class SalaryBracket(str, Enum):
    """Salary range brackets."""
    UNDER_5K    = "< 5 000 DH"
    FROM_5K_10K = "5 000 – 10 000 DH"
    FROM_10K_20K = "10 000 – 20 000 DH"
    ABOVE_20K   = "> 20 000 DH"
    NOT_SPECIFIED = "Non spécifié"


# ── Matching ──────────────────────────────────────────────────────────────────
class MatchScoreLabel(str, Enum):
    """Human-readable label for a match score range."""
    EXCELLENT  = "Excellent"   # ≥ 80 %
    GOOD       = "Good"        # 60 – 79 %
    AVERAGE    = "Average"     # 40 – 59 %
    LOW        = "Low"         # < 40 %

    @classmethod
    def from_score(cls, score: float) -> "MatchScoreLabel":
        """Return the label corresponding to a 0–100 score."""
        if score >= 80:
            return cls.EXCELLENT
        if score >= 60:
            return cls.GOOD
        if score >= 40:
            return cls.AVERAGE
        return cls.LOW


# ── Favorites ─────────────────────────────────────────────────────────────────
class FavoriteStatus(str, Enum):
    """Status of a favorite job."""
    ACTIVE = "active"
    ARCHIVED = "archived"


# ── Notifications ─────────────────────────────────────────────────────────────
class NotificationType(str, Enum):
    """Type of notification."""
    JOB_MATCH = "job_match"
    SKILL_GAP = "skill_gap"
    SYSTEM = "system"
    REMINDER = "reminder"


# ── Gender ────────────────────────────────────────────────────────────────────
class Gender(str, Enum):
    """Gender enumeration."""
    MALE = "male"
    FEMALE = "female"
    OTHER = "other"


# ── Sort Order ────────────────────────────────────────────────────────────────
class SortOrder(str, Enum):
    """Sort order options."""
    ASC = "asc"
    DESC = "desc"


# ── File Type ─────────────────────────────────────────────────────────────────
class FileType(str, Enum):
    """Supported file types for resume upload."""
    PDF = "pdf"
    DOCX = "docx"


# ── Skill Source ──────────────────────────────────────────────────────────────
class SkillSource(str, Enum):
    """Source of skill extraction."""
    PROFILE = "profile"
    RESUME = "resume"
    MANUAL = "manual"


# ── Skill Level ───────────────────────────────────────────────────────────────
class SkillLevel(str, Enum):
    """Skill proficiency level."""
    BEGINNER = "beginner"
    INTERMEDIATE = "intermediate"
    ADVANCED = "advanced"
    EXPERT = "expert"