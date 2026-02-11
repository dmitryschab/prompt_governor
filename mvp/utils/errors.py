"""
Error handling utilities for Prompt Governor API.

Provides custom exceptions, error response formatting, FastAPI exception handlers,
and validation utilities for consistent error handling across the application.
"""

import json
import uuid
from typing import Any, Optional
from fastapi import Request, FastAPI
from fastapi.responses import JSONResponse
from starlette.status import (
    HTTP_400_BAD_REQUEST,
    HTTP_404_NOT_FOUND,
    HTTP_500_INTERNAL_SERVER_ERROR,
)


# =============================================================================
# Custom Exceptions
# =============================================================================


class NotFoundError(Exception):
    """Exception raised when a requested resource is not found (HTTP 404).

    Attributes:
        resource_type: The type of resource that was not found (e.g., "prompt", "config")
        identifier: The identifier that was used to look up the resource
        message: Human-readable error message
    """

    def __init__(
        self, resource_type: str, identifier: str, message: Optional[str] = None
    ):
        self.resource_type = resource_type
        self.identifier = identifier
        self.message = (
            message or f"{resource_type.capitalize()} '{identifier}' not found"
        )
        super().__init__(self.message)


class ValidationError(Exception):
    """Exception raised when request data fails validation (HTTP 400).

    Attributes:
        field: The field that failed validation (optional)
        message: Human-readable validation error message
        details: Additional validation details (e.g., specific errors per field)
    """

    def __init__(
        self,
        message: str,
        field: Optional[str] = None,
        details: Optional[dict[str, Any]] = None,
    ):
        self.message = message
        self.field = field
        self.details = details or {}
        super().__init__(self.message)


class StorageError(Exception):
    """Exception raised when storage operations fail (HTTP 500).

    Attributes:
        operation: The storage operation that failed (e.g., "read", "write")
        path: The file path involved in the operation
        message: Human-readable error message
        cause: The underlying exception that caused this error (optional)
    """

    def __init__(
        self,
        operation: str,
        path: str,
        message: Optional[str] = None,
        cause: Optional[Exception] = None,
    ):
        self.operation = operation
        self.path = path
        self.message = message or f"Failed to {operation} '{path}'"
        self.cause = cause
        super().__init__(self.message)


class PipelineError(Exception):
    """Exception raised when pipeline execution fails (HTTP 500).

    Attributes:
        stage: The pipeline stage that failed (e.g., "extraction", "metrics")
        message: Human-readable error message
        details: Additional error context and information
        cause: The underlying exception that caused this error (optional)
    """

    def __init__(
        self,
        stage: str,
        message: str,
        details: Optional[dict[str, Any]] = None,
        cause: Optional[Exception] = None,
    ):
        self.stage = stage
        self.message = message
        self.details = details or {}
        self.cause = cause
        super().__init__(self.message)


# =============================================================================
# Error Response Formatting
# =============================================================================


def create_error_response(
    message: str,
    details: Optional[dict[str, Any]] = None,
    status_code: int = HTTP_500_INTERNAL_SERVER_ERROR,
) -> dict[str, Any]:
    """Create a standardized error response structure.

    This function returns a dictionary with a consistent error format that can
    be used directly in API responses. The structure follows REST API best
    practices with error type, message, and optional details.

    Args:
        message: The main error message to display to the user
        details: Optional dictionary with additional error details (field errors,
                stack traces for debugging, etc.)
        status_code: HTTP status code for this error (default: 500)

    Returns:
        A dictionary with standardized error structure:
        {
            "error": {
                "type": "error",
                "message": "Human readable message",
                "status_code": 500,
                "details": { ... }  // Optional
            }
        }

    Examples:
        >>> create_error_response("Not found", status_code=404)
        {
            'error': {
                'type': 'error',
                'message': 'Not found',
                'status_code': 404
            }
        }

        >>> create_error_response(
        ...     "Validation failed",
        ...     details={"name": "Name is required"},
        ...     status_code=400
        ... )
        {
            'error': {
                'type': 'error',
                'message': 'Validation failed',
                'status_code': 400,
                'details': {'name': 'Name is required'}
            }
        }
    """
    response = {
        "error": {
            "type": "error",
            "message": message,
            "status_code": status_code,
        }
    }

    if details is not None:
        response["error"]["details"] = details

    return response


def create_validation_error_response(
    field_errors: dict[str, str], message: str = "Validation failed"
) -> dict[str, Any]:
    """Create a validation error response with field-specific errors.

    Args:
        field_errors: Dictionary mapping field names to error messages
        message: General validation error message

    Returns:
        Standardized error response with field details
    """
    return create_error_response(
        message=message,
        details={"fields": field_errors},
        status_code=HTTP_400_BAD_REQUEST,
    )


# =============================================================================
# FastAPI Exception Handlers
# =============================================================================


async def not_found_handler(request: Request, exc: NotFoundError) -> JSONResponse:
    """Handle NotFoundError exceptions.

    Returns a 404 JSON response with resource type and identifier information.
    """
    content = create_error_response(
        message=exc.message,
        details={"resource_type": exc.resource_type, "identifier": exc.identifier},
        status_code=HTTP_404_NOT_FOUND,
    )
    return JSONResponse(status_code=HTTP_404_NOT_FOUND, content=content)


async def validation_error_handler(
    request: Request, exc: ValidationError
) -> JSONResponse:
    """Handle ValidationError exceptions.

    Returns a 400 JSON response with validation details and field information.
    """
    details = dict(exc.details)
    if exc.field:
        details["field"] = exc.field

    content = create_error_response(
        message=exc.message,
        details=details if details else None,
        status_code=HTTP_400_BAD_REQUEST,
    )
    return JSONResponse(status_code=HTTP_400_BAD_REQUEST, content=content)


async def storage_error_handler(request: Request, exc: StorageError) -> JSONResponse:
    """Handle StorageError exceptions.

    Returns a 500 JSON response with operation and path information.
    """
    content = create_error_response(
        message=exc.message,
        details={
            "operation": exc.operation,
            "path": exc.path,
            "cause": str(exc.cause) if exc.cause else None,
        },
        status_code=HTTP_500_INTERNAL_SERVER_ERROR,
    )
    return JSONResponse(status_code=HTTP_500_INTERNAL_SERVER_ERROR, content=content)


async def pipeline_error_handler(request: Request, exc: PipelineError) -> JSONResponse:
    """Handle PipelineError exceptions.

    Returns a 500 JSON response with stage and execution details.
    """
    content = create_error_response(
        message=exc.message,
        details={
            "stage": exc.stage,
            **exc.details,
            "cause": str(exc.cause) if exc.cause else None,
        },
        status_code=HTTP_500_INTERNAL_SERVER_ERROR,
    )
    return JSONResponse(status_code=HTTP_500_INTERNAL_SERVER_ERROR, content=content)


async def generic_404_handler(request: Request, exc: Exception) -> JSONResponse:
    """Handle generic 404 errors (e.g., when endpoint doesn't exist).

    This is registered for the general 404 case when no custom exception is raised.
    """
    content = create_error_response(
        message=f"Endpoint not found: {request.url.path}",
        details={"path": request.url.path, "method": request.method},
        status_code=HTTP_404_NOT_FOUND,
    )
    return JSONResponse(status_code=HTTP_404_NOT_FOUND, content=content)


async def generic_500_handler(request: Request, exc: Exception) -> JSONResponse:
    """Handle generic 500 errors for unhandled exceptions.

    This is a catch-all handler for unexpected errors. In production, you might
    want to limit the error details exposed.
    """
    content = create_error_response(
        message="An unexpected error occurred",
        details={"error_type": type(exc).__name__, "error": str(exc)},
        status_code=HTTP_500_INTERNAL_SERVER_ERROR,
    )
    return JSONResponse(status_code=HTTP_500_INTERNAL_SERVER_ERROR, content=content)


def register_exception_handlers(app: FastAPI) -> None:
    """Register all custom exception handlers with a FastAPI application.

    This function should be called during app initialization to wire up all
    error handlers defined in this module.

    Args:
        app: The FastAPI application instance

    Example:
        >>> from fastapi import FastAPI
        >>> from mvp.utils.errors import register_exception_handlers
        >>>
        >>> app = FastAPI()
        >>> register_exception_handlers(app)
    """
    # Custom exception handlers
    app.add_exception_handler(NotFoundError, not_found_handler)
    app.add_exception_handler(ValidationError, validation_error_handler)
    app.add_exception_handler(StorageError, storage_error_handler)
    app.add_exception_handler(PipelineError, pipeline_error_handler)

    # Generic handlers for standard HTTP exceptions
    # Note: FastAPI has built-in handlers for HTTPException, StarletteHTTPException
    # These are registered as fallback handlers
    app.add_exception_handler(404, generic_404_handler)


# =============================================================================
# Validation Utilities
# =============================================================================


def validate_uuid(id_str: str) -> bool:
    """Validate if a string is a valid UUID format.

    Accepts both standard UUID format (with dashes) and compact format
    (without dashes, 32 hex characters).

    Args:
        id_str: The string to validate as a UUID

    Returns:
        True if valid UUID format, False otherwise

    Examples:
        >>> validate_uuid("550e8400-e29b-41d4-a716-446655440000")
        True
        >>> validate_uuid("550e8400e29b41d4a716446655440000")
        True
        >>> validate_uuid("not-a-uuid")
        False
        >>> validate_uuid("")
        False
    """
    if not id_str or not isinstance(id_str, str):
        return False

    # Handle compact format (32 hex chars without dashes)
    if len(id_str) == 32:
        try:
            uuid.UUID(id_str)
            return True
        except ValueError:
            return False

    # Handle standard format (with dashes)
    try:
        uuid.UUID(id_str)
        return True
    except ValueError:
        return False


def validate_required_fields(
    data: dict[str, Any], fields: list[str]
) -> tuple[bool, list[str]]:
    """Validate that all required fields are present and not empty in the data.

    A field is considered present if:
    - It exists in the data dictionary
    - Its value is not None
    - Its value is not an empty string (if string)
    - Its value is not an empty collection (if list/dict)

    Args:
        data: The dictionary to validate
        fields: List of required field names

    Returns:
        A tuple of (is_valid, missing_fields) where:
        - is_valid: True if all required fields are present
        - missing_fields: List of field names that are missing or empty

    Examples:
        >>> data = {"name": "Test", "description": ""}
        >>> validate_required_fields(data, ["name", "description"])
        (False, ['description'])

        >>> data = {"name": "Test", "tags": ["a", "b"]}
        >>> validate_required_fields(data, ["name", "tags"])
        (True, [])
    """
    missing: list[str] = []

    for field in fields:
        if field not in data:
            missing.append(field)
            continue

        value = data[field]

        # Check for None
        if value is None:
            missing.append(field)
            continue

        # Check for empty string
        if isinstance(value, str) and not value.strip():
            missing.append(field)
            continue

        # Check for empty collections
        if isinstance(value, (list, dict, set, tuple)) and len(value) == 0:
            missing.append(field)
            continue

    return len(missing) == 0, missing


def validate_json(data: Any) -> tuple[bool, Optional[str], Optional[Any]]:
    """Validate that data can be serialized to JSON.

    Performs a round-trip serialization check to ensure the data can be
    properly converted to JSON and back without data loss.

    Args:
        data: The data to validate (can be any Python object)

    Returns:
        A tuple of (is_valid, error_message, parsed_data) where:
        - is_valid: True if data is valid JSON-serializable
        - error_message: Error description if invalid, None if valid
        - parsed_data: The parsed JSON data if valid, None if invalid

    Examples:
        >>> validate_json({"name": "test", "count": 42})
        (True, None, {'name': 'test', 'count': 42})

        >>> validate_json({"data": set([1, 2, 3])})  # Sets aren't JSON serializable
        (False, "Object of type set is not JSON serializable", None)
    """
    try:
        # Serialize to JSON string
        json_str = json.dumps(data)
        # Parse back to verify round-trip works
        parsed = json.loads(json_str)
        return True, None, parsed
    except (TypeError, ValueError) as e:
        return False, str(e), None


def validate_json_string(json_str: str) -> tuple[bool, Optional[str], Optional[Any]]:
    """Validate that a string is valid JSON.

    Args:
        json_str: The JSON string to validate

    Returns:
        A tuple of (is_valid, error_message, parsed_data)

    Examples:
        >>> validate_json_string('{"name": "test"}')
        (True, None, {'name': 'test'})

        >>> validate_json_string('not json')
        (False, 'Expecting value: line 1 column 1 (char 0)', None)
    """
    try:
        parsed = json.loads(json_str)
        return True, None, parsed
    except json.JSONDecodeError as e:
        return False, str(e), None


# =============================================================================
# Utility Functions
# =============================================================================


def format_validation_errors(errors: list[dict[str, Any]]) -> dict[str, str]:
    """Format Pydantic validation errors into a field-based dictionary.

    This utility converts Pydantic's error format into a simpler field->message
    mapping that's easier to display in frontend forms.

    Args:
        errors: List of Pydantic error dictionaries (from ValidationError.errors())

    Returns:
        Dictionary mapping field paths to error messages

    Example:
        >>> errors = [
        ...     {"loc": ["name"], "msg": "field required"},
        ...     {"loc": ["config", "temperature"], "msg": "value must be <= 2.0"}
        ... ]
        >>> format_validation_errors(errors)
        {'name': 'field required', 'config.temperature': 'value must be <= 2.0'}
    """
    formatted: dict[str, str] = {}

    for error in errors:
        # Build field path from loc
        field_path = ".".join(str(loc) for loc in error["loc"])
        formatted[field_path] = error["msg"]

    return formatted
