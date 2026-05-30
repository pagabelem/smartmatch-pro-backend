"""
core/exceptions.py — Custom HTTP exceptions for the entire application.

Why a dedicated exceptions module?
-----------------------------------
FastAPI lets you raise HTTPException anywhere, but hardcoding status codes
and detail strings across modules leads to inconsistent error messages and
makes internationalisation impossible later.

This module provides:
  1. Typed exception classes (one per error family) — raised in services.
  2. A global exception handler registered in main.py that formats ALL errors
     into a single, consistent JSON envelope:

     {
       "success": false,
       "error": {
         "code":    "USER_NOT_FOUND",
         "message": "No user with id 42.",
         "details": null
       }
     }

Usage
-----
  from app.core.exceptions import NotFoundException, UnauthorizedException

  # In a service:
  user = db.get(User, user_id)
  if not user:
      raise NotFoundException("User", user_id)

  # In a router (rarely needed — services should raise):
  raise ForbiddenException("You do not own this resource.")
"""

from typing import Any

from fastapi import HTTPException, Request, status
from fastapi.responses import JSONResponse


# ── Base exception ────────────────────────────────────────────────────────────
class AppException(HTTPException):
    """
    Base class for all SmartMatch application exceptions.

    Attributes
    ----------
    status_code : int
        HTTP status code to return.
    code : str
        Machine-readable error code (SCREAMING_SNAKE_CASE).
        Used by the frontend to show localised messages.
    message : str
        Human-readable description.
    details : Any
        Optional extra context (validation errors, field names, etc.).
    """

    code: str = "INTERNAL_ERROR"

    def __init__(
        self,
        message: str,
        status_code: int = status.HTTP_500_INTERNAL_SERVER_ERROR,
        code: str | None = None,
        details: Any = None,
    ) -> None:
        super().__init__(status_code=status_code, detail=message)
        self.message = message
        self.code = code or self.__class__.code
        self.details = details


# ── 400 Bad Request ───────────────────────────────────────────────────────────
class BadRequestException(AppException):
    """Generic bad request — malformed input that doesn't fit other categories."""
    code = "BAD_REQUEST"

    def __init__(self, message: str = "Bad request.", details: Any = None) -> None:
        super().__init__(message, status.HTTP_400_BAD_REQUEST, details=details)


# ── 401 Unauthorized ──────────────────────────────────────────────────────────
class UnauthorizedException(AppException):
    """Missing or invalid authentication credentials."""
    code = "UNAUTHORIZED"

    def __init__(self, message: str = "Authentication required.") -> None:
        super().__init__(message, status.HTTP_401_UNAUTHORIZED)


class InvalidTokenException(AppException):
    """JWT token is missing, expired, or tampered with."""
    code = "INVALID_TOKEN"

    def __init__(self, message: str = "Invalid or expired token.") -> None:
        super().__init__(message, status.HTTP_401_UNAUTHORIZED)


class InvalidCredentialsException(AppException):
    """Email/password combination is incorrect."""
    code = "INVALID_CREDENTIALS"

    def __init__(self, message: str = "Incorrect email or password.") -> None:
        super().__init__(message, status.HTTP_401_UNAUTHORIZED)


# ── 403 Forbidden ─────────────────────────────────────────────────────────────
class ForbiddenException(AppException):
    """Authenticated but not authorised for this resource/action."""
    code = "FORBIDDEN"

    def __init__(self, message: str = "You do not have permission to perform this action.") -> None:
        super().__init__(message, status.HTTP_403_FORBIDDEN)


# ── 404 Not Found ─────────────────────────────────────────────────────────────
class NotFoundException(AppException):
    """Requested resource does not exist."""
    code = "NOT_FOUND"

    def __init__(self, resource: str = "Resource", identifier: Any = None, message: str = None) -> None:
        """
        Trois modes d'utilisation :
        1. NotFoundException("User", 42) → "User with id '42' not found."
        2. NotFoundException("Resource") → "Resource not found."
        3. NotFoundException(message="CV introuvable (id=1)") → message direct
        """
        if message is not None:
            # Support direct message (ex: "CV introuvable (id=1)")
            super().__init__(message, status.HTTP_404_NOT_FOUND)
        elif identifier is not None:
            msg = f"{resource} with id '{identifier}' not found."
            super().__init__(msg, status.HTTP_404_NOT_FOUND)
        else:
            msg = f"{resource} not found."
            super().__init__(msg, status.HTTP_404_NOT_FOUND)


# ── 409 Conflict ──────────────────────────────────────────────────────────────
class ConflictException(AppException):
    """Resource already exists (e.g. duplicate email)."""
    code = "CONFLICT"

    def __init__(self, message: str = "Resource already exists.") -> None:
        super().__init__(message, status.HTTP_409_CONFLICT)


class EmailAlreadyExistsException(ConflictException):
    """Specific conflict: email already registered."""
    code = "EMAIL_ALREADY_EXISTS"

    def __init__(self, email: str) -> None:
        super().__init__(f"An account with email '{email}' already exists.")


# ── 413 Payload Too Large ─────────────────────────────────────────────────────
class FileTooLargeException(AppException):
    """Uploaded file exceeds the maximum allowed size."""
    code = "FILE_TOO_LARGE"

    def __init__(self, max_mb: int = 5) -> None:
        super().__init__(
            f"File exceeds the maximum allowed size of {max_mb} MB.",
            status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
        )


# ── 415 Unsupported Media Type ────────────────────────────────────────────────
class UnsupportedFileTypeException(AppException):
    """Uploaded file extension is not allowed."""
    code = "UNSUPPORTED_FILE_TYPE"

    def __init__(self, allowed: str = "pdf, docx") -> None:
        super().__init__(
            f"File type not supported. Allowed types: {allowed}.",
            status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
        )


# ── 422 Unprocessable Entity ──────────────────────────────────────────────────
class ValidationException(AppException):
    """Business-logic validation failed (distinct from Pydantic schema errors)."""
    code = "VALIDATION_ERROR"

    def __init__(self, message: str, details: Any = None) -> None:
        super().__init__(message, status.HTTP_422_UNPROCESSABLE_ENTITY, details=details)


# ── 429 Too Many Requests ─────────────────────────────────────────────────────
class RateLimitException(AppException):
    """Client has exceeded the rate limit (e.g. OpenAI API calls)."""
    code = "RATE_LIMIT_EXCEEDED"

    def __init__(self, message: str = "Too many requests. Please wait before retrying.") -> None:
        super().__init__(message, status.HTTP_429_TOO_MANY_REQUESTS)


# ── 503 Service Unavailable ───────────────────────────────────────────────────
class ServiceUnavailableException(AppException):
    """External service (e.g. OpenAI, scraper) is temporarily unavailable."""
    code = "SERVICE_UNAVAILABLE"

    def __init__(self, service: str = "External service") -> None:
        super().__init__(
            f"{service} is temporarily unavailable. Please try again later.",
            status.HTTP_503_SERVICE_UNAVAILABLE,
        )


# ── NLP-specific ──────────────────────────────────────────────────────────────
class NLPProcessingException(AppException):
    """NLP extraction or processing failed."""
    code = "NLP_PROCESSING_ERROR"

    def __init__(self, message: str = "Failed to process text with NLP pipeline.") -> None:
        super().__init__(message, status.HTTP_500_INTERNAL_SERVER_ERROR)


class UnsupportedLanguageException(AppException):
    """Document language is not supported (only FR and EN in V1)."""
    code = "UNSUPPORTED_LANGUAGE"

    def __init__(self, detected: str = "unknown") -> None:
        super().__init__(
            f"Language '{detected}' is not supported. Only French (fr) and English (en) are supported in V1.",
            status.HTTP_422_UNPROCESSABLE_ENTITY,
        )


# ── Global exception handlers (register these in main.py) ────────────────────
async def app_exception_handler(request: Request, exc: AppException) -> JSONResponse:
    """
    Converts any AppException into the standard JSON error envelope.

    Register in main.py:
        from app.core.exceptions import app_exception_handler, AppException
        app.add_exception_handler(AppException, app_exception_handler)
    """
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "success": False,
            "error": {
                "code":    exc.code,
                "message": exc.message,
                "details": exc.details,
            },
        },
    )


async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """
    Catch-all for unexpected exceptions — prevents raw tracebacks leaking to clients.

    Register in main.py:
        app.add_exception_handler(Exception, unhandled_exception_handler)

    In DEBUG mode the real error message is included; in production a generic
    message is shown to avoid leaking implementation details.
    """
    from app.config import settings

    if settings.DEBUG:
        message = f"Unexpected error: {type(exc).__name__}: {exc}"
    else:
        message = "An unexpected internal error occurred."

    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "success": False,
            "error": {
                "code":    "INTERNAL_ERROR",
                "message": message,
                "details": None,
            },
        },
    )