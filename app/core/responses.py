from typing import Any
from fastapi import status
from fastapi.responses import JSONResponse
from fastapi.encoders import jsonable_encoder

# ── Internal builder ──────────────────────────────────────────────────────────
def _success_response(
    data: Any = None,
    message: str | None = None,
    meta: dict | None = None,
    status_code: int = status.HTTP_200_OK,
) -> JSONResponse:
    body: dict[str, Any] = {"success": True}
    
    # Crucial : jsonable_encoder transforme les modèles SQLAlchemy et Datetime en JSON safe
    if data is not None:
        body["data"] = jsonable_encoder(data)
    if message:
        body["message"] = message
    if meta:
        body["meta"] = jsonable_encoder(meta)
        
    return JSONResponse(content=body, status_code=status_code)

# ── Public helpers ────────────────────────────────────────────────────────────
def ok(data: Any = None, message: str | None = None, meta: dict | None = None) -> JSONResponse:
    """HTTP 200 — standard successful response."""
    return _success_response(data, message, meta, status.HTTP_200_OK)

def created(data: Any = None, message: str = "Resource created successfully.") -> JSONResponse:
    """HTTP 201 — resource was just created."""
    return _success_response(data, message, status_code=status.HTTP_201_CREATED)

def no_content() -> JSONResponse:
    """HTTP 204 — action succeeded, nothing to return."""
    return JSONResponse(content=None, status_code=status.HTTP_204_NO_CONTENT)

def accepted(data: Any = None, message: str = "Request accepted and queued for processing.") -> JSONResponse:
    """HTTP 202 — request received but processing is async."""
    return _success_response(data, message, status_code=status.HTTP_202_ACCEPTED)

def paginated(items: list, total: int, page: int, page_size: int, message: str | None = None) -> JSONResponse:
    pages = max(1, -(-total // page_size))
    meta = {
        "total":     total,
        "page":      page,
        "page_size": page_size,
        "pages":     pages,
        "has_next":  page < pages,
        "has_prev":  page > 1,
    }
    return _success_response(items, message, meta, status.HTTP_200_OK)