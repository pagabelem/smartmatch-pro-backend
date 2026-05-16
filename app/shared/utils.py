"""
shared/utils.py — Pure utility functions used across the entire application.

Rules
-----
- Every function here must be stateless and have NO side effects.
- No database, no HTTP calls, no file I/O.
- Each function has a docstring with a concrete example.
"""

import re
import unicodedata
import uuid
from datetime import datetime, timezone
from pathlib import Path


# ── Text / String utilities ───────────────────────────────────────────────────
def slugify(text: str) -> str:
    """
    Convert a string to a URL-safe slug.

    Examples:
        slugify("Data Scientist (Senior)")  → "data-scientist-senior"
        slugify("Développeur Python")       → "developpeur-python"
    """
    text = unicodedata.normalize("NFD", text)
    text = text.encode("ascii", "ignore").decode("ascii")
    text = text.lower()
    text = re.sub(r"[^\w\s-]", "", text)
    text = re.sub(r"[\s_-]+", "-", text)
    return text.strip("-")


def truncate(text: str, max_length: int = 200, suffix: str = "…") -> str:
    """
    Truncate text to max_length characters, appending suffix if cut.

    Example:
        truncate("Hello world", 8)  → "Hello wo…"
    """
    if len(text) <= max_length:
        return text
    return text[: max_length - len(suffix)] + suffix


def clean_whitespace(text: str) -> str:
    """
    Collapse multiple whitespace characters (spaces, tabs, newlines) into one space.

    Example:
        clean_whitespace("hello   \n  world")  → "hello world"
    """
    return re.sub(r"\s+", " ", text).strip()


def strip_html(text: str) -> str:
    """
    Remove HTML tags from a string.

    Example:
        strip_html("<p>Hello <b>world</b></p>")  → "Hello world"
    """
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", text)).strip()


def normalize_skill(skill: str) -> str:
    """
    Normalise a skill string for consistent comparison and deduplication.

    Lowercases, strips punctuation, removes extra spaces.

    Examples:
        normalize_skill("  Python 3 ")   → "python 3"
        normalize_skill("ReactJS")        → "reactjs"
        normalize_skill("Machine Learning") → "machine learning"
    """
    skill = skill.strip().lower()
    skill = re.sub(r"[^\w\s]", "", skill)  # remove punctuation
    skill = clean_whitespace(skill)
    return skill


def extract_emails(text: str) -> list[str]:
    """
    Extract all email addresses from a string.

    Example:
        extract_emails("Contact hr@company.com or info@example.org")
        → ["hr@company.com", "info@example.org"]
    """
    pattern = r"[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}"
    return re.findall(pattern, text)


def mask_email(email: str) -> str:
    """
    Mask an email for display (privacy).

    Example:
        mask_email("alice.martin@example.com")  → "al***@example.com"
    """
    local, domain = email.split("@", 1)
    visible = local[:2] if len(local) > 2 else local[0]
    return f"{visible}***@{domain}"


# ── File utilities ────────────────────────────────────────────────────────────
def generate_unique_filename(original_filename: str) -> str:
    """
    Generate a collision-safe filename by prepending a UUID.

    Preserves the original extension (lowercased).

    Example:
        generate_unique_filename("My CV (final).PDF")
        → "3f2a...8b1c_my-cv-final.pdf"
    """
    path = Path(original_filename)
    extension = path.suffix.lower()          # e.g. ".pdf"
    stem = slugify(path.stem)               # e.g. "my-cv-final"
    unique_id = uuid.uuid4().hex[:12]       # short UUID fragment
    return f"{unique_id}_{stem}{extension}"


def get_file_extension(filename: str) -> str:
    """
    Return the lowercased extension WITHOUT the leading dot.

    Example:
        get_file_extension("report.DOCX")  → "docx"
    """
    return Path(filename).suffix.lstrip(".").lower()


def is_allowed_extension(filename: str, allowed: set[str]) -> bool:
    """
    Check whether a filename has an allowed extension.

    Example:
        is_allowed_extension("cv.pdf", {"pdf", "docx"})  → True
        is_allowed_extension("script.exe", {"pdf", "docx"})  → False
    """
    return get_file_extension(filename) in allowed


# ── Date / Time utilities ─────────────────────────────────────────────────────
def utcnow() -> datetime:
    """Return the current UTC datetime (timezone-aware)."""
    return datetime.now(timezone.utc)


def format_datetime(dt: datetime, fmt: str = "%Y-%m-%d %H:%M UTC") -> str:
    """
    Format a datetime object to a readable string.

    Example:
        format_datetime(utcnow())  → "2025-09-15 10:32 UTC"
    """
    return dt.strftime(fmt)


# ── Numeric / Score utilities ─────────────────────────────────────────────────
def clamp(value: float, min_val: float = 0.0, max_val: float = 100.0) -> float:
    """
    Clamp a float to [min_val, max_val].

    Example:
        clamp(115.3)   → 100.0
        clamp(-5.0)    → 0.0
        clamp(72.5)    → 72.5
    """
    return max(min_val, min(max_val, value))


def round_score(score: float, decimals: int = 1) -> float:
    """
    Round a match score to N decimal places.

    Example:
        round_score(87.6666)  → 87.7
    """
    return round(clamp(score), decimals)


# ── Collection utilities ──────────────────────────────────────────────────────
def deduplicate(items: list, key=None) -> list:
    """
    Remove duplicates from a list while preserving insertion order.

    Parameters
    ----------
    items : list
        The list to deduplicate.
    key : callable | None
        Function to extract the comparison key from each item.
        If None, items are compared directly.

    Examples:
        deduplicate(["python", "sql", "Python", "SQL"],
                     key=str.lower)
        → ["python", "sql"]

        deduplicate([{"id": 1}, {"id": 2}, {"id": 1}],
                     key=lambda x: x["id"])
        → [{"id": 1}, {"id": 2}]
    """
    seen: set = set()
    result = []
    for item in items:
        k = key(item) if key else item
        if k not in seen:
            seen.add(k)
            result.append(item)
    return result


def chunk(lst: list, size: int) -> list[list]:
    """
    Split a list into chunks of at most `size` elements.

    Example:
        chunk([1, 2, 3, 4, 5], 2)  → [[1, 2], [3, 4], [5]]
    """
    return [lst[i : i + size] for i in range(0, len(lst), size)]


def safe_get(d: dict, *keys, default=None):
    """
    Safely traverse a nested dict without raising KeyError.

    Example:
        safe_get({"a": {"b": 42}}, "a", "b")           → 42
        safe_get({"a": {"b": 42}}, "a", "c", default=0) → 0
    """
    for key in keys:
        if not isinstance(d, dict):
            return default
        d = d.get(key, default)
    return d