"""Data models for the Prompt Governor MVP.

This module exports all Pydantic models used throughout the application.

Models:
    PromptVersion: A versioned prompt with content blocks and metadata
    PromptBlock: Individual block within a prompt (title, body, comment)
    ModelConfig: AI model configuration (provider, temperature, etc.)
    Run: A single prompt execution run

Response Schemas:
    ErrorResponse: Standardized error response format
    ListResponse: Paginated list response wrapper
    SuccessResponse: Generic success response wrapper
    ErrorDetail: Detailed error information
    PaginationMeta: Pagination metadata
    HealthResponse: Health check response
"""

from mvp.models.config import ModelConfig
from mvp.models.prompt import PromptBlock, PromptVersion
from mvp.models.responses import (
    ErrorDetail,
    ErrorResponse,
    HealthResponse,
    ListResponse,
    PaginationMeta,
    SuccessResponse,
)
from mvp.models.run import Run

__all__ = [
    # Domain models
    "ModelConfig",
    "PromptBlock",
    "PromptVersion",
    "Run",
    # Response schemas
    "ErrorDetail",
    "ErrorResponse",
    "HealthResponse",
    "ListResponse",
    "PaginationMeta",
    "SuccessResponse",
]
