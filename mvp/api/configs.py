"""Config API endpoints for managing model configurations.

This module provides FastAPI endpoints for:
- Listing all model configurations
- Getting configuration details
- Creating new configurations
- Updating existing configurations
- Deleting configurations
"""

from datetime import datetime
from typing import List, Literal, Optional
from uuid import UUID

from fastapi import APIRouter, HTTPException, Query, Request, status
from pydantic import BaseModel, Field, field_validator

from mvp.models.config import ModelConfig
from mvp.services.storage import (
    generate_id,
    get_collection_path,
    load_index,
    load_json,
    save_index,
    save_json,
)
from mvp.utils.cache import CacheConfig, get_cached, invalidate_namespace, set_cached

router = APIRouter(
    prefix="/api/configs",
    tags=["configs"],
    responses={404: {"description": "Config not found"}},
)


# =============================================================================
# Request/Response Models
# =============================================================================


class ConfigMetadata(BaseModel):
    """Lightweight metadata for config listings."""

    id: str = Field(..., description="Unique identifier (UUID)")
    name: str = Field(..., description="Human-readable name")
    provider: str = Field(..., description="AI provider")
    model_id: str = Field(..., description="Model identifier")
    created_at: datetime = Field(..., description="Creation timestamp")


class ConfigListResponse(BaseModel):
    """Response model for listing configurations."""

    configs: List[ConfigMetadata] = Field(..., description="List of configurations")
    total: int = Field(..., description="Total number of configurations")
    page: int = Field(default=1, description="Current page number")
    page_size: int = Field(default=50, description="Items per page")
    total_pages: int = Field(default=1, description="Total number of pages")


class ConfigCreateRequest(BaseModel):
    """Request model for creating a new configuration.

    ID and created_at are automatically generated.
    """

    name: str = Field(..., description="Human-readable name")
    provider: Literal["openai", "anthropic", "openrouter"] = Field(
        ..., description="AI provider"
    )
    model_id: str = Field(..., description="Specific model identifier")
    reasoning_effort: Optional[str] = Field(
        None, description="Reasoning effort (low, medium, high)"
    )
    temperature: float = Field(
        default=0.7, ge=0.0, le=2.0, description="Sampling temperature (0.0-2.0)"
    )
    max_tokens: Optional[int] = Field(None, ge=1, description="Maximum tokens")
    extra_params: dict = Field(
        default_factory=dict, description="Additional parameters"
    )

    @field_validator("reasoning_effort")
    @classmethod
    def validate_reasoning_effort(cls, v: Optional[str]) -> Optional[str]:
        """Validate reasoning_effort is one of the allowed values."""
        if v is not None and v not in ("low", "medium", "high"):
            raise ValueError("reasoning_effort must be 'low', 'medium', or 'high'")
        return v


class ConfigUpdateRequest(BaseModel):
    """Request model for updating an existing configuration.

    All fields are optional - only provided fields will be updated.
    """

    name: Optional[str] = Field(None, description="Human-readable name")
    provider: Optional[Literal["openai", "anthropic", "openrouter"]] = Field(
        None, description="AI provider"
    )
    model_id: Optional[str] = Field(None, description="Specific model identifier")
    reasoning_effort: Optional[str] = Field(
        None, description="Reasoning effort (low, medium, high)"
    )
    temperature: Optional[float] = Field(
        None, ge=0.0, le=2.0, description="Sampling temperature (0.0-2.0)"
    )
    max_tokens: Optional[int] = Field(None, ge=1, description="Maximum tokens")
    extra_params: Optional[dict] = Field(None, description="Additional parameters")

    @field_validator("reasoning_effort")
    @classmethod
    def validate_reasoning_effort(cls, v: Optional[str]) -> Optional[str]:
        """Validate reasoning_effort is one of the allowed values."""
        if v is not None and v not in ("low", "medium", "high"):
            raise ValueError("reasoning_effort must be 'low', 'medium', or 'high'")
        return v


# =============================================================================
# Helper Functions
# =============================================================================


def _load_config(config_id: str) -> ModelConfig:
    """Load a config from storage by ID.

    Args:
        config_id: The UUID of the config to load

    Returns:
        ModelConfig instance

    Raises:
        HTTPException: 404 if config not found
    """
    configs_path = get_collection_path("configs")
    config_file = configs_path / f"{config_id}.json"

    if not config_file.exists():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Config '{config_id}' not found",
        )

    try:
        data = load_json(config_file)
        return ModelConfig.model_validate(data)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error loading config: {str(e)}",
        )


def _save_config(config: ModelConfig) -> None:
    """Save a config to storage.

    Args:
        config: The ModelConfig to save

    Raises:
        HTTPException: 500 if save fails
    """
    configs_path = get_collection_path("configs")
    config_file = configs_path / f"{config.id}.json"

    try:
        save_json(config_file, config.model_dump(mode="json"))
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error saving config: {str(e)}",
        )


def _update_index(config: ModelConfig) -> None:
    """Update the index with config metadata.

    Args:
        config: The ModelConfig to add/update in index
    """
    index = load_index("configs")

    # Find existing entry or create new
    items = index.get("items", [])
    config_id_str = str(config.id)

    # Remove existing entry if present
    items = [item for item in items if item.get("id") != config_id_str]

    # Add new metadata entry
    metadata = ConfigMetadata(
        id=config_id_str,
        name=config.name,
        provider=config.provider,
        model_id=config.model_id,
        created_at=config.created_at,
    )
    items.append(metadata.model_dump(mode="json"))

    # Sort by name for consistent ordering
    items.sort(key=lambda x: x.get("name", ""))

    index["items"] = items
    save_index("configs", index)


def _remove_from_index(config_id: str) -> None:
    """Remove a config from the index.

    Args:
        config_id: The UUID of the config to remove
    """
    index = load_index("configs")
    items = index.get("items", [])
    items = [item for item in items if item.get("id") != config_id]
    index["items"] = items
    save_index("configs", index)


# =============================================================================
# API Endpoints
# =============================================================================


@router.get(
    "",
    response_model=ConfigListResponse,
    summary="List all configurations",
    description="Returns a paginated list of model configurations with metadata.",
)
async def list_configs(
    request: Request,
    page: int = Query(1, ge=1, description="Page number (1-indexed)"),
    page_size: int = Query(50, ge=1, le=100, description="Items per page (max 100)"),
) -> ConfigListResponse:
    """List configurations with pagination.

    Args:
        request: FastAPI request object
        page: Page number (1-indexed, default: 1)
        page_size: Items per page (default: 50, max: 100)

    Returns:
        ConfigListResponse containing paginated configs
    """
    # Build cache key
    cache_key = f"configs:page={page}:size={page_size}"

    # Try to get from cache
    cached = await get_cached(cache_key, namespace="configs")
    if cached:
        return ConfigListResponse(**cached)

    index = load_index("configs")
    items = index.get("items", [])

    # Calculate pagination
    total = len(items)
    total_pages = (total + page_size - 1) // page_size if total > 0 else 1

    # Ensure page is within bounds
    if page > total_pages:
        page = max(1, total_pages)

    # Slice items for current page
    start_idx = (page - 1) * page_size
    end_idx = start_idx + page_size
    paginated_items = items[start_idx:end_idx]

    configs = [ConfigMetadata.model_validate(item) for item in paginated_items]

    result = ConfigListResponse(
        configs=configs,
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages,
    )

    # Cache the result
    await set_cached(
        cache_key, result.model_dump(), CacheConfig.CONFIG_LIST_TTL, namespace="configs"
    )

    return result


@router.get(
    "/{config_id}",
    response_model=ModelConfig,
    summary="Get configuration by ID",
    description="Returns the complete configuration including all parameters.",
)
async def get_config(config_id: str) -> ModelConfig:
    """Get a configuration by its ID.

    Args:
        config_id: The UUID of the configuration

    Returns:
        Complete ModelConfig with all fields

    Raises:
        HTTPException: 404 if config not found
    """
    return _load_config(config_id)


@router.post(
    "",
    response_model=ModelConfig,
    status_code=status.HTTP_201_CREATED,
    summary="Create configuration",
    description="Create a new model configuration with validation.",
)
async def create_config(request: ConfigCreateRequest) -> ModelConfig:
    """Create a new configuration.

    Generates a new UUID and sets created_at automatically.
    Validates provider and temperature range.

    Args:
        request: Configuration data (without id and created_at)

    Returns:
        The created ModelConfig with generated id and created_at
    """
    # Create new config with generated ID and timestamp
    config = ModelConfig(
        id=UUID(generate_id()),
        name=request.name,
        provider=request.provider,
        model_id=request.model_id,
        reasoning_effort=request.reasoning_effort,
        temperature=request.temperature,
        max_tokens=request.max_tokens,
        extra_params=request.extra_params,
        created_at=datetime.utcnow(),
    )

    # Save to storage
    _save_config(config)

    # Update index
    _update_index(config)

    # Invalidate configs cache
    await invalidate_namespace("configs")

    return config


@router.put(
    "/{config_id}",
    response_model=ModelConfig,
    summary="Update configuration",
    description="Update an existing configuration. Only provided fields are updated.",
)
async def update_config(
    config_id: str,
    request: ConfigUpdateRequest,
) -> ModelConfig:
    """Update an existing configuration.

    Args:
        config_id: The UUID of the configuration to update
        request: Fields to update (only provided fields are modified)

    Returns:
        The updated ModelConfig

    Raises:
        HTTPException: 404 if config not found
    """
    # Load existing config
    config = _load_config(config_id)

    # Update fields if provided
    if request.name is not None:
        config.name = request.name

    if request.provider is not None:
        config.provider = request.provider

    if request.model_id is not None:
        config.model_id = request.model_id

    if request.reasoning_effort is not None:
        config.reasoning_effort = request.reasoning_effort

    if request.temperature is not None:
        config.temperature = request.temperature

    if request.max_tokens is not None:
        config.max_tokens = request.max_tokens

    if request.extra_params is not None:
        config.extra_params = request.extra_params

    # Save updated config
    _save_config(config)

    # Update index (name might have changed)
    _update_index(config)

    # Invalidate configs cache
    await invalidate_namespace("configs")

    return config


@router.delete(
    "/{config_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete configuration",
    description="Delete a configuration by ID.",
)
async def delete_config(config_id: str) -> None:
    """Delete a configuration.

    Args:
        config_id: The UUID of the configuration to delete

    Raises:
        HTTPException: 404 if config not found
    """
    # Check if config exists
    configs_path = get_collection_path("configs")
    config_file = configs_path / f"{config_id}.json"

    if not config_file.exists():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Config '{config_id}' not found",
        )

    # Delete the file
    try:
        config_file.unlink()
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error deleting config: {str(e)}",
        )

    # Update index
    _remove_from_index(config_id)

    # Invalidate configs cache
    await invalidate_namespace("configs")

    return None
