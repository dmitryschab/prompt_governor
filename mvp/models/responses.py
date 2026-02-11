"""Common API response schemas for standardized API responses.

This module provides standardized response models for all API endpoints
to ensure consistent response structure across the application.

All responses follow a common pattern:
    - success: Boolean indicating success or failure
    - data: The actual response payload (on success)
    - error: Error details (on failure)
    - meta: Metadata like pagination, timing, etc.
"""

from typing import Any, Dict, Generic, List, Optional, TypeVar
from uuid import UUID

from pydantic import BaseModel, Field

T = TypeVar("T")


class ErrorDetail(BaseModel):
    """Detailed error information for API error responses."""

    code: str = Field(..., description="Error code for programmatic handling")
    message: str = Field(..., description="Human-readable error message")
    field: Optional[str] = Field(
        None, description="Field that caused the error (for validation errors)"
    )
    details: Optional[Dict[str, Any]] = Field(
        None, description="Additional error context"
    )

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "code": "VALIDATION_ERROR",
                    "message": "Field 'name' is required",
                    "field": "name",
                    "details": {"provided": None, "expected": "string"},
                },
                {
                    "code": "NOT_FOUND",
                    "message": "Prompt version not found",
                    "field": None,
                    "details": {"resource_id": "123e4567-e89b-12d3-a456-426614174000"},
                },
            ]
        }
    }


class ErrorResponse(BaseModel):
    """Standardized error response for all API errors.

    Use this for all error responses to ensure clients can handle
    errors consistently.

    Examples:
        >>> # 404 Not Found
        >>> ErrorResponse(
        ...     success=False,
        ...     error=ErrorDetail(
        ...         code="NOT_FOUND",
        ...         message="Document 'report.pdf' not found"
        ...     )
        ... )
        >>>
        >>> # 400 Validation Error
        >>> ErrorResponse(
        ...     success=False,
        ...     error=ErrorDetail(
        ...         code="VALIDATION_ERROR",
        ...         message="Invalid temperature value",
        ...         field="temperature"
        ...     )
        ... )
    """

    success: bool = Field(default=False, description="Always false for error responses")
    error: ErrorDetail = Field(..., description="Error details")

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "success": False,
                    "error": {
                        "code": "NOT_FOUND",
                        "message": "Prompt version not found",
                        "field": None,
                        "details": {"id": "123e4567-e89b-12d3-a456-426614174000"},
                    },
                },
                {
                    "success": False,
                    "error": {
                        "code": "VALIDATION_ERROR",
                        "message": "Temperature must be between 0.0 and 2.0",
                        "field": "temperature",
                        "details": {"min": 0.0, "max": 2.0, "provided": 3.5},
                    },
                },
            ]
        }
    }


class PaginationMeta(BaseModel):
    """Pagination metadata for list responses."""

    page: int = Field(default=1, ge=1, description="Current page number")
    per_page: int = Field(default=20, ge=1, le=100, description="Items per page")
    total: int = Field(default=0, ge=0, description="Total number of items")
    total_pages: int = Field(default=0, ge=0, description="Total number of pages")
    has_next: bool = Field(default=False, description="Whether there are more pages")
    has_prev: bool = Field(
        default=False, description="Whether there are previous pages"
    )

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "page": 1,
                    "per_page": 20,
                    "total": 45,
                    "total_pages": 3,
                    "has_next": True,
                    "has_prev": False,
                },
                {
                    "page": 2,
                    "per_page": 20,
                    "total": 45,
                    "total_pages": 3,
                    "has_next": True,
                    "has_prev": True,
                },
            ]
        }
    }


class ListResponse(BaseModel, Generic[T]):
    """Standardized list response with pagination support.

    Use this for any endpoint that returns a list of items.
    Supports generic typing for type-safe responses.

    Examples:
        >>> # Typed list response
        >>> response: ListResponse[PromptVersion] = ListResponse(
        ...     success=True,
        ...     data=[prompt1, prompt2],
        ...     meta=PaginationMeta(page=1, per_page=20, total=2)
        ... )
        >>>
        >>> # Simple untyped list
        >>> ListResponse(data=[{"id": 1}, {"id": 2}])
    """

    success: bool = Field(
        default=True, description="Always true for successful responses"
    )
    data: List[T] = Field(default_factory=list, description="List of items")
    meta: PaginationMeta = Field(
        default_factory=lambda: PaginationMeta(), description="Pagination metadata"
    )

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "success": True,
                    "data": [
                        {"id": "uuid-1", "name": "Item 1"},
                        {"id": "uuid-2", "name": "Item 2"},
                    ],
                    "meta": {
                        "page": 1,
                        "per_page": 20,
                        "total": 2,
                        "total_pages": 1,
                        "has_next": False,
                        "has_prev": False,
                    },
                }
            ]
        }
    }


class SuccessResponse(BaseModel, Generic[T]):
    """Standardized success response for single item operations.

    Use this for endpoints that return a single item or confirmation
    of a successful operation.

    Examples:
        >>> # Single item response
        >>> SuccessResponse(data=prompt_version)
        >>>
        >>> # Simple confirmation
        >>> SuccessResponse(
        ...     data={"deleted": True},
        ...     message="Item successfully deleted"
        ... )
        >>>
        >>> # With metadata
        >>> SuccessResponse(
        ...     data=run_result,
        ...     meta={"processing_time_ms": 1234}
        ... )
    """

    success: bool = Field(
        default=True, description="Always true for successful responses"
    )
    data: Optional[T] = Field(None, description="Response data payload")
    message: Optional[str] = Field(None, description="Optional success message")
    meta: Optional[Dict[str, Any]] = Field(None, description="Additional metadata")

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "success": True,
                    "data": {
                        "id": "123e4567-e89b-12d3-a456-426614174000",
                        "name": "Test",
                    },
                    "message": "Item created successfully",
                    "meta": {"created_at": "2024-01-15T10:30:00Z"},
                },
                {
                    "success": True,
                    "data": None,
                    "message": "Item deleted successfully",
                    "meta": {"deleted_at": "2024-01-15T10:30:00Z"},
                },
            ]
        }
    }


class HealthResponse(BaseModel):
    """Health check response model."""

    status: str = Field(..., description="Current service status")
    version: str = Field(..., description="Application version")
    timestamp: Optional[str] = Field(None, description="Response timestamp")
    uptime_seconds: Optional[float] = Field(
        None, description="Service uptime in seconds"
    )

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "status": "healthy",
                    "version": "0.1.0",
                    "timestamp": "2024-01-15T10:30:00Z",
                    "uptime_seconds": 3600.5,
                }
            ]
        }
    }


# Type aliases for common response patterns
PromptListResponse = ListResponse[Dict[str, Any]]
ConfigListResponse = ListResponse[Dict[str, Any]]
RunListResponse = ListResponse[Dict[str, Any]]
DocumentListResponse = ListResponse[Dict[str, Any]]
