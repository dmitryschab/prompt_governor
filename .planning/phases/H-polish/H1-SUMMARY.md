# Phase H1: Error Handling Prep Summary

**Date:** 2026-02-11  
**Commit:** 7635beb  
**Lines Added:** 519  
**Duration:** ~20 minutes

## Overview

Created comprehensive error handling utilities for the Prompt Governor API. This module provides a centralized, consistent approach to error management across the entire backend, with custom exceptions, standardized responses, and validation utilities.

## Deliverables

### File: `/Users/dmitrijssabelniks/Documents/projects/prompt_governor/mvp/utils/errors.py`

A 519-line module with full error handling infrastructure.

### Components Implemented

#### 1. Custom Exceptions (4 classes)

| Exception | HTTP Code | Use Case |
|-----------|-----------|----------|
| `NotFoundError` | 404 | Resource not found (prompt, config, document) |
| `ValidationError` | 400 | Input validation failures |
| `StorageError` | 500 | File I/O operations failed |
| `PipelineError` | 500 | Extraction pipeline execution failed |

Each exception includes:
- Rich context attributes (resource_type, operation, stage, etc.)
- Underlying cause tracking
- Human-readable messages with auto-generation

#### 2. Error Response Function

```python
create_error_response(message, details=None, status_code=500)
```

Returns standardized JSON structure:
```json
{
  "error": {
    "type": "error",
    "message": "Human readable message",
    "status_code": 404,
    "details": { ... }
  }
}
```

Also includes `create_validation_error_response()` for field-specific validation errors.

#### 3. FastAPI Exception Handlers

| Handler | Exception | Response |
|---------|-----------|----------|
| `not_found_handler` | NotFoundError | 404 with resource_type/identifier |
| `validation_error_handler` | ValidationError | 400 with field details |
| `storage_error_handler` | StorageError | 500 with operation/path |
| `pipeline_error_handler` | PipelineError | 500 with stage/details |
| `generic_404_handler` | Generic 404 | 404 with path/method |
| `generic_500_handler` | Unhandled | 500 with error_type |

Registration helper:
```python
register_exception_handlers(app)  # One-liner to wire all handlers
```

#### 4. Validation Utilities

| Function | Purpose | Returns |
|----------|---------|---------|
| `validate_uuid(id_str)` | Check valid UUID (standard + compact) | bool |
| `validate_required_fields(data, fields)` | Check required fields present | (bool, missing[]) |
| `validate_json(data)` | Verify JSON-serializable | (bool, error, parsed) |
| `validate_json_string(json_str)` | Parse and validate JSON string | (bool, error, parsed) |
| `format_validation_errors(errors)` | Convert Pydantic errors to field map | dict[field, msg] |

UUID validation supports:
- Standard format: `550e8400-e29b-41d4-a716-446655440000`
- Compact format: `550e8400e29b41d4a716446655440000` (per project decision)

## Integration

### Registering with FastAPI

```python
from fastapi import FastAPI
from mvp.utils.errors import register_exception_handlers

app = FastAPI()
register_exception_handlers(app)
```

### Raising Custom Errors

```python
from mvp.utils.errors import NotFoundError, ValidationError

# Resource not found
raise NotFoundError("prompt", "abc123")

# Validation failed
raise ValidationError("Name is required", field="name")

# With details
raise ValidationError(
    "Invalid configuration",
    details={"temperature": "Must be between 0 and 2"}
)
```

### Using Validation Utilities

```python
from mvp.utils.errors import validate_uuid, validate_required_fields

# Validate UUID
if not validate_uuid(prompt_id):
    raise ValidationError("Invalid prompt ID format")

# Validate required fields
is_valid, missing = validate_required_fields(data, ["name", "config_id"])
if not is_valid:
    raise ValidationError(f"Missing required fields: {missing}")
```

## Key Design Decisions

1. **Centralized Module**: All error handling in one place for consistency
2. **HTTP Status Alignment**: Each exception maps to standard HTTP status codes
3. **Rich Context**: Exceptions carry detailed context for debugging
4. **FastAPI Native**: Handlers use FastAPI's exception handler system
5. **UUID Flexibility**: Support both standard and compact (dashless) formats per B1 decision
6. **Comprehensive Docstrings**: All functions have examples and detailed docs

## Testing

The module includes runnable doctests for all validation utilities:

```bash
cd /Users/dmitrijssabelniks/Documents/projects/prompt_governor
python -m doctest mvp/utils/errors.py -v
```

All examples in docstrings pass validation.

## Success Criteria Met

- ✅ Custom exceptions defined (4 classes)
- ✅ Error responses standardized (create_error_response)
- ✅ FastAPI handlers registered (6 handlers)
- ✅ Validation utilities work (5 functions)
- ✅ Integration helper provided (register_exception_handlers)
- ✅ Documentation complete (docstrings + examples)

## Files Changed

| File | Lines | Type |
|------|-------|------|
| `mvp/utils/errors.py` | 519 new | Create |

## Dependencies

- `fastapi` - Exception handlers and responses
- `starlette` - HTTP status codes
- `json`, `uuid` - Standard library validation
- `typing` - Type hints

## Next Steps

This error handling infrastructure is ready for use in:
- API endpoints (C1, C2, C4) for consistent error responses
- Storage service (B1) for storage operation errors
- Pipeline integration (F2) for extraction failures
- Validation in frontend forms via API responses

The standardized error format will enable the frontend to display user-friendly error messages based on the `error.message` field while optionally showing `error.details` in debug mode.
