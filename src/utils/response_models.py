"""
Standard Response Models for API endpoints.

Use these models to ensure consistent response format across all endpoints:
- success: boolean indicating operation success
- data: the actual response payload
- message: optional message for context
- error: error details when success=False
"""

from typing import Any, Optional, List, Generic, TypeVar
from pydantic import BaseModel, Field

T = TypeVar('T')


class APIResponse(BaseModel):
    """Standard API response wrapper."""
    success: bool = True
    data: Optional[Any] = None
    message: Optional[str] = None
    error: Optional[str] = None

    class Config:
        json_schema_extra = {
            "example": {
                "success": True,
                "data": {"id": 1, "name": "Example"},
                "message": "Operation completed"
            }
        }


class PaginatedResponse(BaseModel):
    """Response with pagination metadata."""
    success: bool = True
    data: List[Any] = Field(default_factory=list)
    count: int = 0
    total: int = 0
    page: int = 1
    page_size: int = 20


class ErrorResponse(BaseModel):
    """Standard error response."""
    success: bool = False
    error: str
    detail: Optional[str] = None
    code: Optional[str] = None


# Helper function for creating responses
def success_response(data: Any = None, message: str = None) -> dict:
    """Create a standard success response dict."""
    response = {"success": True}
    if data is not None:
        response["data"] = data
    if message:
        response["message"] = message
    return response


def error_response(error: str, detail: str = None, code: str = None) -> dict:
    """Create a standard error response dict."""
    response = {"success": False, "error": error}
    if detail:
        response["detail"] = detail
    if code:
        response["code"] = code
    return response
