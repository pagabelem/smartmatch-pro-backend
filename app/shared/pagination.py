"""
shared/pagination.py — Reusable pagination logic for all list endpoints.

Pattern used: offset/limit pagination (simplest, works for all DB backends).
Cursor-based pagination can be added in V2 for very large datasets.

Usage in a router
-----------------
  from app.shared.pagination import PaginationParams, paginate_query

  @router.get("/jobs")
  def list_jobs(
      params: PaginationParams = Depends(),
      db: Session = Depends(get_db),
  ):
      query = db.query(Job).filter(Job.status == JobStatus.ACTIVE)
      page  = paginate_query(query, params)
      return paginated(
          items     = page.items,
          total     = page.total,
          page      = page.page,
          page_size = page.page_size,
      )
"""

from dataclasses import dataclass
from typing import Any, Generic, TypeVar

from fastapi import Query
from sqlalchemy.orm import Query as SAQuery

from app.core.constants import DEFAULT_PAGE, DEFAULT_PAGE_SIZE, MAX_PAGE_SIZE

T = TypeVar("T")


# ── Query parameter model ─────────────────────────────────────────────────────
class PaginationParams:
    """
    Injects `page` and `page_size` as query parameters.

    Example URL: GET /jobs?page=2&page_size=10
    """

    def __init__(
        self,
        page: int = Query(
            default=DEFAULT_PAGE,
            ge=1,
            description="Page number (1-based).",
        ),
        page_size: int = Query(
            default=DEFAULT_PAGE_SIZE,
            ge=1,
            le=MAX_PAGE_SIZE,
            description=f"Items per page (max {MAX_PAGE_SIZE}).",
        ),
    ) -> None:
        self.page      = page
        self.page_size = page_size

    @property
    def offset(self) -> int:
        """SQL OFFSET value derived from page and page_size."""
        return (self.page - 1) * self.page_size

    @property
    def limit(self) -> int:
        """SQL LIMIT value — same as page_size."""
        return self.page_size


# ── Result container ──────────────────────────────────────────────────────────
@dataclass
class Page(Generic[T]):
    """
    Container returned by paginate_query().

    Attributes
    ----------
    items     : list of ORM objects for the current page.
    total     : total number of matching rows (for computing `pages`).
    page      : current page number.
    page_size : number of items per page.
    pages     : total number of pages.
    has_next  : True if there is a next page.
    has_prev  : True if there is a previous page.
    """
    items:     list[T]
    total:     int
    page:      int
    page_size: int

    @property
    def pages(self) -> int:
        return max(1, -(-self.total // self.page_size))  # ceiling division

    @property
    def has_next(self) -> bool:
        return self.page < self.pages

    @property
    def has_prev(self) -> bool:
        return self.page > 1

    def to_dict(self) -> dict[str, Any]:
        """Serialize meta for the API response envelope."""
        return {
            "total":     self.total,
            "page":      self.page,
            "page_size": self.page_size,
            "pages":     self.pages,
            "has_next":  self.has_next,
            "has_prev":  self.has_prev,
        }


# ── Core helper ───────────────────────────────────────────────────────────────
def paginate_query(query: SAQuery, params: PaginationParams) -> Page:
    """
    Apply offset/limit pagination to a SQLAlchemy query.

    Executes TWO queries:
      1. COUNT(*) — to get the total number of matching rows.
      2. SELECT with OFFSET/LIMIT — to get the current page items.

    Parameters
    ----------
    query  : A SQLAlchemy Query object (already filtered/sorted).
    params : PaginationParams injected from the route.

    Returns
    -------
    Page object with items + metadata.

    Example:
        query  = db.query(Job).filter(Job.status == "active").order_by(Job.created_at.desc())
        params = PaginationParams(page=2, page_size=20)
        page   = paginate_query(query, params)
        # page.items    → list of Job objects for page 2
        # page.total    → e.g. 87
        # page.pages    → 5
        # page.has_next → True
    """
    total = query.count()
    items = query.offset(params.offset).limit(params.limit).all()
    return Page(
        items     = items,
        total     = total,
        page      = params.page,
        page_size = params.page_size,
    )


# ── List-based pagination (when you already have all items in memory) ─────────
def paginate_list(items: list[T], params: PaginationParams) -> Page[T]:
    """
    Paginate a Python list (no DB query needed).

    Use this when the full list is already in memory (e.g. NLP results,
    in-memory skill lists).

    Example:
        all_skills = ["Python", "SQL", "Java", ...]   # 150 items
        page = paginate_list(all_skills, PaginationParams(page=1, page_size=20))
        # page.items → first 20 skills
    """
    total = len(items)
    start = params.offset
    end   = start + params.limit
    return Page(
        items     = items[start:end],
        total     = total,
        page      = params.page,
        page_size = params.page_size,
    )