"""Prompt management API endpoints.

This module provides FastAPI endpoints for:
- Listing, creating, reading, updating, and deleting prompts
- Comparing different prompt versions with diff functionality
"""

from datetime import datetime
from typing import Any, List, Optional
from uuid import UUID

from fastapi import APIRouter, HTTPException, Query, Request, status
from pydantic import BaseModel, Field

from mvp.models.prompt import PromptBlock, PromptVersion
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
    prefix="/api/prompts",
    tags=["prompts"],
    responses={404: {"description": "Prompt not found"}},
)


# =============================================================================
# Response Models
# =============================================================================


class PromptMetadata(BaseModel):
    """Lightweight metadata for a prompt (for listing)."""

    id: str = Field(..., description="Unique identifier")
    name: str = Field(..., description="Name of the prompt")
    description: Optional[str] = Field(None, description="Optional description")
    created_at: datetime = Field(..., description="Creation timestamp")
    parent_id: Optional[str] = Field(None, description="Parent version ID if forked")
    tags: List[str] = Field(default_factory=list, description="Tags for categorization")

    class Config:
        """Pydantic configuration."""

        json_schema_extra = {
            "example": {
                "id": "550e8400e29b41d4a716446655440000",
                "name": "Contract Extractor",
                "description": "Extracts key fields from insurance contracts",
                "created_at": "2026-02-11T10:30:00",
                "parent_id": None,
                "tags": ["extraction", "contracts"],
            }
        }


class PromptListResponse(BaseModel):
    """Response model for listing prompts."""

    prompts: List[PromptMetadata] = Field(..., description="List of prompt metadata")
    total: int = Field(..., description="Total number of prompts")
    page: int = Field(default=1, description="Current page number")
    page_size: int = Field(default=50, description="Items per page")
    total_pages: int = Field(default=1, description="Total number of pages")


class PromptCreateRequest(BaseModel):
    """Request model for creating a new prompt."""

    name: str = Field(..., description="Name of the prompt")
    description: Optional[str] = Field(None, description="Optional description")
    blocks: List[PromptBlock] = Field(default_factory=list, description="Prompt blocks")
    parent_id: Optional[str] = Field(None, description="Parent version ID if forking")
    tags: List[str] = Field(default_factory=list, description="Tags for categorization")


class PromptUpdateRequest(BaseModel):
    """Request model for updating a prompt."""

    name: Optional[str] = Field(None, description="Name of the prompt")
    description: Optional[str] = Field(None, description="Optional description")
    blocks: Optional[List[PromptBlock]] = Field(None, description="Prompt blocks")
    tags: Optional[List[str]] = Field(None, description="Tags for categorization")


class BlockDiff(BaseModel):
    """Difference information for a single block."""

    index: int = Field(..., description="Block index")
    status: str = Field(..., description="added, removed, or modified")
    old_block: Optional[dict] = Field(None, description="Previous block content")
    new_block: Optional[dict] = Field(None, description="New block content")


class PromptDiffResponse(BaseModel):
    """Response model for comparing two prompts."""

    prompt_a_id: str = Field(..., description="First prompt ID")
    prompt_b_id: str = Field(..., description="Second prompt ID")
    name_changed: bool = Field(..., description="Whether name differs")
    description_changed: bool = Field(..., description="Whether description differs")
    tags_changed: bool = Field(..., description="Whether tags differ")
    blocks_diff: List[BlockDiff] = Field(
        default_factory=list, description="Differences in blocks"
    )


# =============================================================================
# Helper Functions
# =============================================================================


def _get_prompts_collection_path():
    """Get the path to the prompts collection directory."""
    return get_collection_path("prompts")


def _prompt_file_path(prompt_id: str) -> Any:
    """Get the file path for a specific prompt."""
    return _get_prompts_collection_path() / f"{prompt_id}.json"


def _load_prompt(prompt_id: str) -> dict:
    """Load a prompt from storage by ID.

    Args:
        prompt_id: The prompt ID to load

    Returns:
        Dictionary containing prompt data

    Raises:
        HTTPException: 404 if prompt not found
    """
    file_path = _prompt_file_path(prompt_id)
    try:
        return load_json(file_path)
    except FileNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Prompt '{prompt_id}' not found",
        )


def _save_prompt(prompt_id: str, data: dict) -> None:
    """Save a prompt to storage.

    Args:
        prompt_id: The prompt ID
        data: The prompt data to save
    """
    file_path = _prompt_file_path(prompt_id)
    save_json(file_path, data)


def _update_index_for_prompt(prompt_data: dict, operation: str = "add") -> None:
    """Update the index file when a prompt is added or removed.

    Args:
        prompt_data: The prompt data
        operation: Either 'add' or 'remove'
    """
    index = load_index("prompts")

    # Initialize items list if not exists
    if "items" not in index:
        index["items"] = []

    # Ensure all items have required fields
    for item in index["items"]:
        if "tags" not in item:
            item["tags"] = []

    if operation == "add":
        # Check if already exists (update case)
        existing_idx = None
        for idx, item in enumerate(index["items"]):
            if item.get("id") == prompt_data["id"]:
                existing_idx = idx
                break

        metadata = {
            "id": prompt_data["id"],
            "name": prompt_data["name"],
            "description": prompt_data.get("description"),
            "created_at": prompt_data["created_at"],
            "parent_id": prompt_data.get("parent_id"),
            "tags": prompt_data.get("tags", []),
        }

        if existing_idx is not None:
            index["items"][existing_idx] = metadata
        else:
            index["items"].append(metadata)

    elif operation == "remove":
        index["items"] = [
            item for item in index["items"] if item.get("id") != prompt_data["id"]
        ]

    # Sort by created_at descending (newest first)
    index["items"].sort(key=lambda x: x.get("created_at", ""), reverse=True)

    save_index("prompts", index)


def _prompt_data_to_metadata(prompt_data: dict) -> PromptMetadata:
    """Convert prompt data dictionary to PromptMetadata."""
    return PromptMetadata(
        id=prompt_data["id"],
        name=prompt_data["name"],
        description=prompt_data.get("description"),
        created_at=datetime.fromisoformat(
            prompt_data["created_at"].replace("Z", "+00:00")
        ),
        parent_id=prompt_data.get("parent_id"),
        tags=prompt_data.get("tags", []),
    )


def _compare_blocks(blocks_a: List[dict], blocks_b: List[dict]) -> List[BlockDiff]:
    """Compare two lists of blocks and return differences.

    Args:
        blocks_a: First list of blocks
        blocks_b: Second list of blocks

    Returns:
        List of BlockDiff objects
    """
    diffs = []

    # Use a simple diff algorithm
    max_len = max(len(blocks_a), len(blocks_b))

    for i in range(max_len):
        block_a = blocks_a[i] if i < len(blocks_a) else None
        block_b = blocks_b[i] if i < len(blocks_b) else None

        if block_a is None and block_b is not None:
            # Added in B
            diffs.append(
                BlockDiff(index=i, status="added", old_block=None, new_block=block_b)
            )
        elif block_a is not None and block_b is None:
            # Removed in B
            diffs.append(
                BlockDiff(index=i, status="removed", old_block=block_a, new_block=None)
            )
        elif block_a != block_b:
            # Modified
            diffs.append(
                BlockDiff(
                    index=i,
                    status="modified",
                    old_block=block_a,
                    new_block=block_b,
                )
            )

    return diffs


# =============================================================================
# API Endpoints
# =============================================================================


@router.get(
    "",
    response_model=PromptListResponse,
    summary="List all prompts",
    description="Returns a paginated list of prompts with metadata. Supports filtering by tags.",
)
async def list_prompts(
    request: Request,
    page: int = Query(1, ge=1, description="Page number (1-indexed)"),
    page_size: int = Query(50, ge=1, le=100, description="Items per page (max 100)"),
    tag: Optional[List[str]] = Query(
        None, description="Filter by tags (can specify multiple)"
    ),
) -> PromptListResponse:
    """List prompts with pagination and optional tag filtering.

    Args:
        request: FastAPI request object
        page: Page number (1-indexed, default: 1)
        page_size: Items per page (default: 50, max: 100)
        tag: Optional list of tags to filter by

    Returns:
        PromptListResponse containing paginated prompts
    """
    # Build cache key
    cache_key = (
        f"prompts:page={page}:size={page_size}:tags={','.join(sorted(tag or []))}"
    )

    # Try to get from cache
    cached = await get_cached(cache_key, namespace="prompts")
    if cached:
        return PromptListResponse(**cached)

    index = load_index("prompts")
    items = index.get("items", [])

    # Filter by tags if specified
    if tag:
        tag_set = set(t.lower() for t in tag)
        filtered_items = []
        for item in items:
            item_tags = set(t.lower() for t in item.get("tags", []))
            if tag_set & item_tags:  # Intersection - any matching tag
                filtered_items.append(item)
        items = filtered_items

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

    # Convert to metadata objects
    prompts = [_prompt_data_to_metadata(item) for item in paginated_items]

    result = PromptListResponse(
        prompts=prompts,
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages,
    )

    # Cache the result
    await set_cached(
        cache_key, result.model_dump(), CacheConfig.PROMPT_LIST_TTL, namespace="prompts"
    )

    return result


@router.get(
    "/{prompt_id}",
    response_model=PromptVersion,
    summary="Get prompt by ID",
    description="Returns the complete prompt version including all blocks.",
)
async def get_prompt(prompt_id: str) -> PromptVersion:
    """Get a complete prompt by ID.

    Args:
        prompt_id: The unique prompt identifier

    Returns:
        Complete PromptVersion object

    Raises:
        HTTPException: 404 if prompt not found
    """
    prompt_data = _load_prompt(prompt_id)
    return PromptVersion.model_validate(prompt_data)


@router.post(
    "",
    response_model=PromptVersion,
    status_code=status.HTTP_201_CREATED,
    summary="Create new prompt",
    description="Creates a new prompt version with auto-generated ID and timestamp.",
)
async def create_prompt(request: PromptCreateRequest) -> PromptVersion:
    """Create a new prompt version.

    Args:
        request: The prompt creation request

    Returns:
        The created PromptVersion
    """
    # Generate new ID and timestamp
    prompt_id = generate_id()
    created_at = datetime.utcnow()

    # Build prompt data
    prompt_data = {
        "id": prompt_id,
        "name": request.name,
        "description": request.description,
        "blocks": [block.model_dump() for block in request.blocks],
        "created_at": created_at.isoformat() + "Z",
        "parent_id": request.parent_id,
        "tags": request.tags,
    }

    # Save to storage
    _save_prompt(prompt_id, prompt_data)

    # Update index
    _update_index_for_prompt(prompt_data, operation="add")

    # Invalidate prompts cache
    await invalidate_namespace("prompts")

    # Return as PromptVersion
    return PromptVersion.model_validate(prompt_data)


@router.put(
    "/{prompt_id}",
    response_model=PromptVersion,
    summary="Update prompt",
    description="Updates an existing prompt. All fields are optional - only provided fields are updated.",
)
async def update_prompt(prompt_id: str, request: PromptUpdateRequest) -> PromptVersion:
    """Update an existing prompt.

    Args:
        prompt_id: The prompt ID to update
        request: The update request with fields to change

    Returns:
        The updated PromptVersion

    Raises:
        HTTPException: 404 if prompt not found
    """
    # Load existing prompt
    prompt_data = _load_prompt(prompt_id)

    # Update fields if provided
    if request.name is not None:
        prompt_data["name"] = request.name
    if request.description is not None:
        prompt_data["description"] = request.description
    if request.blocks is not None:
        prompt_data["blocks"] = [block.model_dump() for block in request.blocks]
    if request.tags is not None:
        prompt_data["tags"] = request.tags

    # Save updated prompt
    _save_prompt(prompt_id, prompt_data)

    # Update index
    _update_index_for_prompt(prompt_data, operation="add")

    # Invalidate prompts cache
    await invalidate_namespace("prompts")

    return PromptVersion.model_validate(prompt_data)


@router.delete(
    "/{prompt_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete prompt",
    description="Deletes a prompt and updates the index.",
)
async def delete_prompt(prompt_id: str) -> None:
    """Delete a prompt.

    Args:
        prompt_id: The prompt ID to delete

    Raises:
        HTTPException: 404 if prompt not found
    """
    # Verify prompt exists
    prompt_data = _load_prompt(prompt_id)

    # Delete the file
    file_path = _prompt_file_path(prompt_id)
    file_path.unlink()

    # Update index
    _update_index_for_prompt(prompt_data, operation="remove")

    # Invalidate prompts cache
    await invalidate_namespace("prompts")


@router.get(
    "/{prompt_id}/diff/{other_id}",
    response_model=PromptDiffResponse,
    summary="Compare two prompts",
    description="Returns a diff showing differences between two prompt versions.",
)
async def compare_prompts(prompt_id: str, other_id: str) -> PromptDiffResponse:
    """Compare two prompt versions.

    Args:
        prompt_id: First prompt ID
        other_id: Second prompt ID

    Returns:
        PromptDiffResponse with detailed differences

    Raises:
        HTTPException: 404 if either prompt not found
    """
    # Load both prompts
    prompt_a = _load_prompt(prompt_id)
    prompt_b = _load_prompt(other_id)

    # Compare simple fields
    name_changed = prompt_a.get("name") != prompt_b.get("name")
    description_changed = prompt_a.get("description") != prompt_b.get("description")
    tags_changed = set(prompt_a.get("tags", [])) != set(prompt_b.get("tags", []))

    # Compare blocks
    blocks_a = prompt_a.get("blocks", [])
    blocks_b = prompt_b.get("blocks", [])
    blocks_diff = _compare_blocks(blocks_a, blocks_b)

    return PromptDiffResponse(
        prompt_a_id=prompt_id,
        prompt_b_id=other_id,
        name_changed=name_changed,
        description_changed=description_changed,
        tags_changed=tags_changed,
        blocks_diff=blocks_diff,
    )
