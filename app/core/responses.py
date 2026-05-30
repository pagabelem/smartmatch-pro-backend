"""
Standardized API response formats.
"""

from typing import Any, Dict, Generic, List, Optional, TypeVar, Union
from pydantic import BaseModel, Field

T = TypeVar("T")


class StandardResponse(BaseModel, Generic[T]):
    """Standard API response wrapper."""
    
    success: bool = Field(True, description="Indicates if the request was successful")
    data: Optional[T] = Field(None, description="Response data payload")
    message: Optional[str] = Field(None, description="Optional response message")
    errors: Optional[List[Dict[str, Any]]] = Field(None, description="Validation errors if any")


class PaginatedResponse(BaseModel, Generic[T]):
    """Paginated response wrapper."""
    
    items: List[T] = Field(..., description="List of items for current page")
    total: int = Field(..., description="Total number of items")
    page: int = Field(..., description="Current page number")
    limit: int = Field(..., description="Items per page")
    pages: int = Field(..., description="Total number of pages")


def success_response(
    data: Any = None,
    message: Optional[str] = None,
) -> Dict[str, Any]:
    """Create a standardized success response."""
    return {
        "success": True,
        "data": data,
        "message": message,
    }


def error_response(
    message: str,
    code: str = "ERROR",
    details: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Create a standardized error response."""
    response = {
        "success": False,
        "error": {
            "code": code,
            "message": message,
        },
    }
    if details:
        response["error"]["details"] = details
    return response


def ok(
    data: Any = None,
    message: Optional[str] = None,
) -> Dict[str, Any]:
    """Alias for success_response for GET/PUT/DELETE operations."""
    return success_response(data, message)


def created(
    data: Any = None,
    message: str = "Resource created successfully",
) -> Dict[str, Any]:
    """Response for successful POST/CREATE operations."""
    return {
        "success": True,
        "data": data,
        "message": message,
    }


def no_content(
    message: str = "Resource deleted successfully",
) -> Dict[str, Any]:
    """Response for successful DELETE operations (204 No Content)."""
    return {
        "success": True,
        "data": None,
        "message": message,
    }


def not_found(
    resource: str,
    identifier: Any = None,
) -> Dict[str, Any]:
    """Response for not found errors."""
    message = f"{resource} not found"
    if identifier:
        message += f": {identifier}"
    return error_response(message, code="NOT_FOUND")


def bad_request(
    message: str,
    details: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Response for bad request errors."""
    return error_response(message, code="BAD_REQUEST", details=details)


def unauthorized(
    message: str = "Unauthorized",
) -> Dict[str, Any]:
    """Response for unauthorized access."""
    return error_response(message, code="UNAUTHORIZED")


def forbidden(
    message: str = "Forbidden",
) -> Dict[str, Any]:
    """Response for forbidden access."""
    return error_response(message, code="FORBIDDEN")