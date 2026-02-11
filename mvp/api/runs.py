"""Runs API endpoints for managing extraction runs.

This module provides FastAPI endpoints for:
- Listing runs with filtering
- Getting run details and results
- Creating and executing new runs
- Comparing runs
- Deleting runs

Note: This is a minimal stub implementation. Full implementation
requires Phase B4 (Executor Service) and pipeline integration.
"""

from datetime import datetime
from typing import Any, List, Optional
from uuid import UUID

from fastapi import APIRouter, HTTPException, Query, status
from pydantic import BaseModel, Field

from mvp.services.storage import (
    generate_id,
    get_collection_path,
    load_index,
    load_json,
    save_index,
    save_json,
)

router = APIRouter(
    prefix="/api/runs",
    tags=["runs"],
    responses={404: {"description": "Run not found"}},
)


# =============================================================================
# Response Models
# =============================================================================


class RunMetadata(BaseModel):
    """Lightweight metadata for run listings."""

    id: str = Field(..., description="Unique identifier")
    prompt_id: str = Field(..., description="ID of the prompt used")
    config_id: str = Field(..., description="ID of the config used")
    document_name: str = Field(..., description="Name of the document processed")
    status: str = Field(
        ..., description="Run status: pending, running, completed, failed"
    )
    created_at: datetime = Field(..., description="Creation timestamp")
    completed_at: Optional[datetime] = Field(None, description="Completion timestamp")
    metrics: Optional[dict] = Field(
        None, description="Run metrics (recall, precision, F1)"
    )


class RunListResponse(BaseModel):
    """Response model for listing runs."""

    runs: List[RunMetadata] = Field(..., description="List of run metadata")
    total: int = Field(..., description="Total number of runs")


class RunDetailResponse(BaseModel):
    """Complete run details including output."""

    id: str = Field(..., description="Unique identifier")
    prompt_id: str = Field(..., description="ID of the prompt used")
    config_id: str = Field(..., description="ID of the config used")
    document_name: str = Field(..., description="Name of the document processed")
    status: str = Field(..., description="Run status")
    created_at: datetime = Field(..., description="Creation timestamp")
    started_at: Optional[datetime] = Field(None, description="When run started")
    completed_at: Optional[datetime] = Field(None, description="When run completed")
    output: Optional[dict] = Field(None, description="Extraction output")
    metrics: Optional[dict] = Field(None, description="Run metrics")
    cost_usd: Optional[float] = Field(None, description="Cost in USD")
    tokens: Optional[dict] = Field(
        None, description="Token usage (prompt, completion, total)"
    )
    error: Optional[str] = Field(None, description="Error message if failed")


class RunCreateRequest(BaseModel):
    """Request model for creating a new run."""

    prompt_id: str = Field(..., description="ID of the prompt to use")
    config_id: str = Field(..., description="ID of the config to use")
    document_name: str = Field(..., description="Name of the document to process")


class RunCompareResponse(BaseModel):
    """Response for comparing two runs."""

    run_a_id: str = Field(..., description="First run ID")
    run_b_id: str = Field(..., description="Second run ID")
    differences: dict = Field(..., description="Detailed differences")


# =============================================================================
# Helper Functions
# =============================================================================


def _get_runs_collection_path():
    """Get the path to the runs collection directory."""
    return get_collection_path("runs")


def _run_file_path(run_id: str) -> Any:
    """Get the file path for a specific run."""
    return _get_runs_collection_path() / f"{run_id}.json"


def _load_run(run_id: str) -> dict:
    """Load a run from storage by ID."""
    file_path = _run_file_path(run_id)
    try:
        return load_json(file_path)
    except FileNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Run '{run_id}' not found",
        )


def _run_data_to_metadata(run_data: dict) -> RunMetadata:
    """Convert run data dictionary to RunMetadata."""
    created_at = run_data.get("created_at")
    completed_at = run_data.get("completed_at")

    if isinstance(created_at, str):
        created_at = datetime.fromisoformat(created_at.replace("Z", "+00:00"))
    if isinstance(completed_at, str):
        completed_at = datetime.fromisoformat(completed_at.replace("Z", "+00:00"))

    return RunMetadata(
        id=run_data["id"],
        prompt_id=run_data.get("prompt_id", ""),
        config_id=run_data.get("config_id", ""),
        document_name=run_data.get("document_name", ""),
        status=run_data.get("status", "unknown"),
        created_at=created_at or datetime.utcnow(),
        completed_at=completed_at,
        metrics=run_data.get("metrics"),
    )


# =============================================================================
# API Endpoints
# =============================================================================


@router.get(
    "",
    response_model=RunListResponse,
    summary="List all runs",
    description="Returns a list of all runs with metadata. Supports filtering by prompt_id and config_id.",
)
async def list_runs(
    prompt_id: Optional[str] = Query(None, description="Filter by prompt ID"),
    config_id: Optional[str] = Query(None, description="Filter by config ID"),
    status: Optional[str] = Query(None, description="Filter by status"),
) -> RunListResponse:
    """List all runs with optional filtering."""
    index = load_index("runs")
    items = index.get("items", [])

    # Apply filters
    if prompt_id:
        items = [item for item in items if item.get("prompt_id") == prompt_id]
    if config_id:
        items = [item for item in items if item.get("config_id") == config_id]
    if status:
        items = [item for item in items if item.get("status") == status]

    # Convert to metadata objects
    runs = [_run_data_to_metadata(item) for item in items]

    # Sort by created_at descending (newest first)
    runs.sort(key=lambda x: x.created_at, reverse=True)

    return RunListResponse(runs=runs, total=len(runs))


@router.get(
    "/{run_id}",
    response_model=RunDetailResponse,
    summary="Get run details",
    description="Returns complete run details including output and metrics.",
)
async def get_run(run_id: str) -> RunDetailResponse:
    """Get a complete run by ID."""
    run_data = _load_run(run_id)

    # Parse timestamps
    for field in ["created_at", "started_at", "completed_at"]:
        if field in run_data and isinstance(run_data[field], str):
            run_data[field] = datetime.fromisoformat(
                run_data[field].replace("Z", "+00:00")
            )

    return RunDetailResponse(**run_data)


@router.post(
    "",
    response_model=RunDetailResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create new run",
    description="Creates a new run and queues it for execution. (Stub: creates pending run)",
)
async def create_run(request: RunCreateRequest) -> RunDetailResponse:
    """Create a new run.

    Note: This is a stub implementation. Full implementation requires
    Phase B4 (Executor Service) integration with the pipeline.
    """
    run_id = generate_id()
    created_at = datetime.utcnow()

    run_data = {
        "id": run_id,
        "prompt_id": request.prompt_id,
        "config_id": request.config_id,
        "document_name": request.document_name,
        "status": "pending",
        "created_at": created_at.isoformat() + "Z",
        "started_at": None,
        "completed_at": None,
        "output": None,
        "metrics": None,
        "cost_usd": None,
        "tokens": None,
        "error": None,
    }

    # Save run
    _get_runs_collection_path().mkdir(parents=True, exist_ok=True)
    save_json(_run_file_path(run_id), run_data)

    # Update index
    index = load_index("runs")
    if "items" not in index:
        index["items"] = []
    index["items"].append(run_data)
    save_index("runs", index)

    return RunDetailResponse(**run_data)


@router.delete(
    "/{run_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete run",
    description="Deletes a run and updates the index.",
)
async def delete_run(run_id: str) -> None:
    """Delete a run."""
    # Verify run exists
    run_data = _load_run(run_id)

    # Delete file
    file_path = _run_file_path(run_id)
    file_path.unlink()

    # Update index
    index = load_index("runs")
    index["items"] = [item for item in index["items"] if item.get("id") != run_id]
    save_index("runs", index)

    return None


@router.get(
    "/{run_id}/compare/{other_id}",
    response_model=RunCompareResponse,
    summary="Compare two runs",
    description="Compare outputs and metrics between two runs.",
)
async def compare_runs(run_id: str, other_id: str) -> RunCompareResponse:
    """Compare two runs."""
    # Load both runs
    run_a = _load_run(run_id)
    run_b = _load_run(other_id)

    # Build differences
    differences = {
        "prompt_id_changed": run_a.get("prompt_id") != run_b.get("prompt_id"),
        "config_id_changed": run_a.get("config_id") != run_b.get("config_id"),
        "document_changed": run_a.get("document_name") != run_b.get("document_name"),
        "metrics_diff": {},
        "output_diff": {},
    }

    # Compare metrics if available
    metrics_a = run_a.get("metrics") or {}
    metrics_b = run_b.get("metrics") or {}
    for key in set(list(metrics_a.keys()) + list(metrics_b.keys())):
        if metrics_a.get(key) != metrics_b.get(key):
            differences["metrics_diff"][key] = {
                "run_a": metrics_a.get(key),
                "run_b": metrics_b.get(key),
            }

    # Compare outputs if available
    output_a = run_a.get("output") or {}
    output_b = run_b.get("output") or {}
    differences["output_diff"] = {
        "keys_a": list(output_a.keys()),
        "keys_b": list(output_b.keys()),
        "shared_keys": list(set(output_a.keys()) & set(output_b.keys())),
    }

    return RunCompareResponse(
        run_a_id=run_id,
        run_b_id=other_id,
        differences=differences,
    )
