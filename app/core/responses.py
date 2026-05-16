"""
core/responses.py — Standardised JSON response helpers.

Every API endpoint returns the same envelope, whether it succeeds or fails:

  Success:
    {
      "success": true,
      "data":    { ... },        ← the actual payload
      "message": "User created.", ← optional human-readable confirmation
      "meta":    { ... }         ← optional pagination / extra context
    }

  Error (handled by exceptions.py):
    {
      "success": false,
      "error": {
        "code":    "NOT_FOUND",
        "message": "User with id 42 not found.",
        "details": null
      }
    }

Usage in a router
-----------------
  from app.core.responses import ok, created, no_content, paginated

  @router.get("/jobs/{job_id}")
  def get_job(job_id: int, db: Session = Depends(get_db)):
      job = job_service.get_by_id(db, job_id)
      return ok(data=job, message="Job retrieved.")

  @router.post("/jobs", status_code=201)
  def create_job(...):
      job = job_service.create(db, payload)
      return created(data=job, message="Job created successfully.")
"""

from typing import Any

from fastapi import status
from fastapi.responses import JSONResponse


# ── Internal builder ──────────────────────────────────────────────────────────
def _success_response(
    data: Any = None,
    message: str | None = None,
    meta: dict | None = None,
    status_code: int = status.HTTP_200_OK,
) -> JSONResponse:
    body: dict[str, Any] = {"success": True}
    if data is not None:
        body["data"] = data
    if message:
        body["message"] = message
    if meta:
        body["meta"] = meta
    return JSONResponse(content=body, status_code=status_code)


# ── Public helpers ────────────────────────────────────────────────────────────
def ok(
    data: Any = None,
    message: str | None = None,
    meta: dict | None = None,
) -> JSONResponse:
    """HTTP 200 — standard successful response."""
    return _success_response(data, message, meta, status.HTTP_200_OK)


def created(
    data: Any = None,
    message: str = "Resource created successfully.",
) -> JSONResponse:
    """HTTP 201 — resource was just created."""
    return _success_response(data, message, status_code=status.HTTP_201_CREATED)


def no_content() -> JSONResponse:
    """HTTP 204 — action succeeded, nothing to return (e.g. DELETE)."""
    return JSONResponse(content=None, status_code=status.HTTP_204_NO_CONTENT)


def accepted(
    data: Any = None,
    message: str = "Request accepted and queued for processing.",
) -> JSONResponse:
    """HTTP 202 — request received but processing is async (e.g. NLP batch)."""
    return _success_response(data, message, status_code=status.HTTP_202_ACCEPTED)


def paginated(
    items: list,
    total: int,
    page: int,
    page_size: int,
    message: str | None = None,
) -> JSONResponse:
    """
    HTTP 200 with pagination metadata in `meta`.

    Example response:
        {
          "success": true,
          "data": [ ... ],
          "meta": {
            "total":      87,
            "page":       2,
            "page_size":  20,
            "pages":      5,
            "has_next":   true,
            "has_prev":   true
          }
        }
    """
    pages = max(1, -(-total // page_size))   # ceiling division
    meta = {
        "total":     total,
        "page":      page,
        "page_size": page_size,
        "pages":     pages,
        "has_next":  page < pages,
        "has_prev":  page > 1,
    }
    return _success_response(items, message, meta, status.HTTP_200_OK)