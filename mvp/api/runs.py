"""Run execution API endpoints for prompt governor.

This module provides FastAPI endpoints for:
- Listing runs with filtering
- Getting run details
- Creating and executing new runs (async)
- Deleting runs
- Comparing two runs
"""

import asyncio
from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import UUID

from fastapi import APIRouter, BackgroundTasks, HTTPException, Query, status
from pydantic import BaseModel, Field

from mvp.models import Run, SuccessResponse, ListResponse
from mvp.models.responses import PaginationMeta
from mvp.services.executor import execute_run
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
# Request/Response Models
# =============================================================================


class RunMetadata(BaseModel):
    """Lightweight metadata for run listings (performance optimized)."""

    id: str = Field(..., description="Unique identifier")
    prompt_id: str = Field(..., description="ID of the prompt used")
    config_id: str = Field(..., description="ID of the config used")
    document_name: str = Field(..., description="Name of the document processed")
    status: str = Field(
        ..., description="Current status (pending/running/completed/failed)"
    )
    started_at: str = Field(..., description="When the run started")
    completed_at: Optional[str] = Field(None, description="When the run completed")
    cost_usd: Optional[float] = Field(None, description="Cost of the run in USD")

    class Config:
        """Pydantic configuration."""

        json_schema_extra = {
            "example": {
                "id": "550e8400e29b41d4a716446655440000",
                "prompt_id": "660f9511f30a52e5b827557766551111",
                "config_id": "7710a622g41b63f6c938668877662222",
                "document_name": "contract_001.pdf",
                "status": "completed",
                "started_at": "2026-02-11T10:30:00Z",
                "completed_at": "2026-02-11T10:30:05Z",
                "cost_usd": 0.045,
            }
        }


class RunListResponse(BaseModel):
    """Response model for listing runs."""

    runs: List[RunMetadata] = Field(..., description="List of run metadata")
    total: int = Field(..., description="Total number of runs")


class RunCreateRequest(BaseModel):
    """Request model for creating a new run."""

    prompt_id: str = Field(..., description="ID of the prompt to use")
    config_id: str = Field(..., description="ID of the config to use")
    document_name: str = Field(..., description="Name of the document to process")


class RunCreateResponse(BaseModel):
    """Response for creating a new run (202 Accepted)."""

    run_id: str = Field(..., description="ID of the created run")
    status: str = Field(default="pending", description="Initial status")
    message: str = Field(
        default="Run queued for execution", description="Status message"
    )


class RunComparison(BaseModel):
    """Comparison data for a single run."""

    run_id: str = Field(..., description="Run ID")
    prompt_id: str = Field(..., description="Prompt ID used")
    config_id: str = Field(..., description="Config ID used")
    document_name: str = Field(..., description="Document name")
    status: str = Field(..., description="Run status")
    metrics: Optional[Dict[str, Any]] = Field(None, description="Run metrics")


class MetricComparison(BaseModel):
    """Comparison of a single metric between two runs."""

    metric: str = Field(..., description="Metric name")
    run_a_value: Optional[float] = Field(None, description="Value in run A")
    run_b_value: Optional[float] = Field(None, description="Value in run B")
    difference: Optional[float] = Field(None, description="Absolute difference")
    percent_change: Optional[float] = Field(None, description="Percentage change")


class FieldDifference(BaseModel):
    """Difference in a single field between two outputs."""

    field: str = Field(..., description="Field name")
    run_a_value: Any = Field(None, description="Value in run A")
    run_b_value: Any = Field(None, description="Value in run B")
    status: str = Field(..., description="same, different, only_in_a, or only_in_b")


class RunCompareResponse(BaseModel):
    """Response model for comparing two runs."""

    run_a: RunComparison = Field(..., description="First run data")
    run_b: RunComparison = Field(..., description="Second run data")
    metric_comparisons: List[MetricComparison] = Field(
        default_factory=list, description="Metrics compared side by side"
    )
    field_differences: List[FieldDifference] = Field(
        default_factory=list, description="Differences in output fields"
    )
    summary: Dict[str, Any] = Field(
        default_factory=dict, description="Summary of comparison"
    )


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
    """Load a run from storage by ID.

    Args:
        run_id: The run ID to load

    Returns:
        Dictionary containing run data

    Raises:
        HTTPException: 404 if run not found
    """
    file_path = _run_file_path(run_id)
    try:
        return load_json(file_path)
    except FileNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Run '{run_id}' not found",
        )


def _save_run(run_id: str, data: dict) -> None:
    """Save a run to storage.

    Args:
        run_id: The run ID
        data: The run data to save
    """
    file_path = _run_file_path(run_id)
    save_json(file_path, data)


def _update_index_for_run(run_data: dict, operation: str = "add") -> None:
    """Update the index file when a run is added or removed.

    Args:
        run_data: The run data
        operation: Either 'add' or 'remove'
    """
    index = load_index("runs")

    # Initialize items list if not exists
    if "items" not in index:
        index["items"] = []

    if operation == "add":
        # Check if already exists
        existing_idx = None
        for idx, item in enumerate(index["items"]):
            if item.get("id") == run_data["id"]:
                existing_idx = idx
                break

        metadata = RunMetadata(
            id=run_data["id"],
            prompt_id=run_data["prompt_id"],
            config_id=run_data["config_id"],
            document_name=run_data["document_name"],
            status=run_data["status"],
            started_at=run_data["started_at"],
            completed_at=run_data.get("completed_at"),
            cost_usd=run_data.get("cost_usd"),
        )

        if existing_idx is not None:
            index["items"][existing_idx] = metadata.model_dump()
        else:
            index["items"].append(metadata.model_dump())

    elif operation == "remove":
        index["items"] = [
            item for item in index["items"] if item.get("id") != run_data["id"]
        ]

    # Sort by started_at descending (newest first)
    index["items"].sort(key=lambda x: x.get("started_at", ""), reverse=True)

    save_index("runs", index)


def _run_data_to_metadata(run_data: dict) -> RunMetadata:
    """Convert run data dictionary to RunMetadata."""
    return RunMetadata(
        id=run_data["id"],
        prompt_id=run_data["prompt_id"],
        config_id=run_data["config_id"],
        document_name=run_data["document_name"],
        status=run_data["status"],
        started_at=run_data["started_at"],
        completed_at=run_data.get("completed_at"),
        cost_usd=run_data.get("cost_usd"),
    )


def _validate_prompt_exists(prompt_id: str) -> None:
    """Validate that a prompt exists.

    Args:
        prompt_id: The prompt ID to validate

    Raises:
        HTTPException: 404 if prompt not found
    """
    prompts_path = get_collection_path("prompts")
    prompt_file = prompts_path / f"{prompt_id}.json"
    if not prompt_file.exists():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Prompt '{prompt_id}' not found",
        )


def _validate_config_exists(config_id: str) -> None:
    """Validate that a config exists.

    Args:
        config_id: The config ID to validate

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


def _validate_document_exists(document_name: str) -> None:
    """Validate that a document exists.

    Args:
        document_name: The document name to validate

    Raises:
        HTTPException: 404 if document not found
    """
    # Documents are in the documents/ directory
    docs_path = get_collection_path("..") / "documents"
    doc_file = docs_path / document_name
    if not doc_file.exists():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Document '{document_name}' not found",
        )


def _compare_metrics(
    metrics_a: Optional[Dict[str, Any]],
    metrics_b: Optional[Dict[str, Any]],
) -> List[MetricComparison]:
    """Compare metrics between two runs.

    Args:
        metrics_a: Metrics from run A
        metrics_b: Metrics from run B

    Returns:
        List of metric comparisons
    """
    comparisons = []
    metric_keys = set()

    if metrics_a:
        metric_keys.update(metrics_a.keys())
    if metrics_b:
        metric_keys.update(metrics_b.keys())

    # Only compare numeric metrics
    numeric_keys = {"recall", "precision", "f1", "latency_ms", "accuracy"}
    metric_keys = metric_keys & numeric_keys

    for key in sorted(metric_keys):
        val_a = metrics_a.get(key) if metrics_a else None
        val_b = metrics_b.get(key) if metrics_b else None

        # Ensure values are numeric
        if val_a is not None and not isinstance(val_a, (int, float)):
            val_a = None
        if val_b is not None and not isinstance(val_b, (int, float)):
            val_b = None

        difference = None
        percent_change = None

        if val_a is not None and val_b is not None:
            difference = round(val_b - val_a, 4)
            if val_a != 0:
                percent_change = round(((val_b - val_a) / val_a) * 100, 2)

        comparisons.append(
            MetricComparison(
                metric=key,
                run_a_value=val_a,
                run_b_value=val_b,
                difference=difference,
                percent_change=percent_change,
            )
        )

    return comparisons


def _compare_outputs(
    output_a: Optional[Dict[str, Any]],
    output_b: Optional[Dict[str, Any]],
) -> List[FieldDifference]:
    """Compare outputs between two runs.

    Args:
        output_a: Output from run A
        output_b: Output from run B

    Returns:
        List of field differences
    """
    differences = []
    all_fields = set()

    if output_a:
        all_fields.update(output_a.keys())
    if output_b:
        all_fields.update(output_b.keys())

    for field in sorted(all_fields):
        val_a = output_a.get(field) if output_a else None
        val_b = output_b.get(field) if output_b else None

        if val_a is None and val_b is not None:
            status = "only_in_b"
        elif val_a is not None and val_b is None:
            status = "only_in_a"
        elif val_a == val_b:
            status = "same"
        else:
            status = "different"

        differences.append(
            FieldDifference(
                field=field,
                run_a_value=val_a,
                run_b_value=val_b,
                status=status,
            )
        )

    return differences


def _create_comparison_summary(
    run_a: dict,
    run_b: dict,
    metric_comparisons: List[MetricComparison],
    field_differences: List[FieldDifference],
) -> Dict[str, Any]:
    """Create a summary of the comparison.

    Args:
        run_a: Run A data
        run_b: Run B data
        metric_comparisons: Metric comparisons
        field_differences: Field differences

    Returns:
        Summary dictionary
    """
    same_prompt = run_a.get("prompt_id") == run_b.get("prompt_id")
    same_config = run_a.get("config_id") == run_b.get("config_id")
    same_document = run_a.get("document_name") == run_b.get("document_name")

    different_fields = [d for d in field_differences if d.status == "different"]
    same_fields = [d for d in field_differences if d.status == "same"]

    return {
        "same_prompt": same_prompt,
        "same_config": same_config,
        "same_document": same_document,
        "total_fields_compared": len(field_differences),
        "fields_same": len(same_fields),
        "fields_different": len(different_fields),
        "fields_only_in_run_a": len(
            [d for d in field_differences if d.status == "only_in_a"]
        ),
        "fields_only_in_run_b": len(
            [d for d in field_differences if d.status == "only_in_b"]
        ),
    }


# =============================================================================
# API Endpoints
# =============================================================================


@router.get(
    "",
    response_model=RunListResponse,
    summary="List all runs",
    description="Returns a list of all runs with metadata. Supports filtering by prompt_id, config_id, document_name, and status.",
)
async def list_runs(
    prompt_id: Optional[str] = Query(None, description="Filter by prompt ID"),
    config_id: Optional[str] = Query(None, description="Filter by config ID"),
    document_name: Optional[str] = Query(None, description="Filter by document name"),
    status: Optional[str] = Query(
        None, description="Filter by status (pending/running/completed/failed)"
    ),
) -> RunListResponse:
    """List all runs with optional filtering.

    Args:
        prompt_id: Optional filter by prompt ID
        config_id: Optional filter by config ID
        document_name: Optional filter by document name
        status: Optional filter by status

    Returns:
        RunListResponse containing filtered runs
    """
    index = load_index("runs")
    items = index.get("items", [])

    # Apply filters
    if prompt_id:
        items = [item for item in items if item.get("prompt_id") == prompt_id]

    if config_id:
        items = [item for item in items if item.get("config_id") == config_id]

    if document_name:
        items = [item for item in items if item.get("document_name") == document_name]

    if status:
        items = [item for item in items if item.get("status") == status]

    # Convert to metadata objects
    runs = [_run_data_to_metadata(item) for item in items]

    return RunListResponse(runs=runs, total=len(runs))


@router.get(
    "/{run_id}",
    response_model=Run,
    summary="Get run details",
    description="Returns the complete run object including output and metrics.",
)
async def get_run(run_id: str) -> Run:
    """Get a complete run by ID.

    Args:
        run_id: The unique run identifier

    Returns:
        Complete Run object

    Raises:
        HTTPException: 404 if run not found
    """
    run_data = _load_run(run_id)
    return Run.model_validate(run_data)


@router.post(
    "",
    response_model=RunCreateResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Execute new run",
    description="Creates a new run and executes it asynchronously. Returns 202 Accepted with run ID.",
)
async def create_run(
    request: RunCreateRequest,
    background_tasks: BackgroundTasks,
) -> RunCreateResponse:
    """Create and queue a new run for execution.

    Validates that all referenced resources exist, creates the run with
    pending status, and queues it for async execution.

    Args:
        request: The run creation request
        background_tasks: FastAPI background tasks for async execution

    Returns:
        RunCreateResponse with run ID and status

    Raises:
        HTTPException: 404 if prompt, config, or document not found
    """
    # Validate all IDs exist
    _validate_prompt_exists(request.prompt_id)
    _validate_config_exists(request.config_id)
    _validate_document_exists(request.document_name)

    # Generate new ID and timestamp
    run_id = generate_id()
    started_at = datetime.utcnow()

    # Build run data
    run_data = {
        "id": run_id,
        "prompt_id": request.prompt_id,
        "config_id": request.config_id,
        "document_name": request.document_name,
        "status": "pending",
        "started_at": started_at.isoformat() + "Z",
        "completed_at": None,
        "output": None,
        "metrics": None,
        "cost_usd": None,
        "tokens": None,
    }

    # Save to storage
    _save_run(run_id, run_data)

    # Update index
    _update_index_for_run(run_data, operation="add")

    # Queue for async execution
    background_tasks.add_task(
        execute_run,
        run_id=run_id,
        prompt_id=request.prompt_id,
        config_id=request.config_id,
        document_name=request.document_name,
    )

    return RunCreateResponse(
        run_id=run_id,
        status="pending",
        message="Run queued for execution",
    )


@router.delete(
    "/{run_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete run",
    description="Deletes a run and updates the index.",
)
async def delete_run(run_id: str) -> None:
    """Delete a run.

    Args:
        run_id: The run ID to delete

    Raises:
        HTTPException: 404 if run not found
    """
    # Verify run exists
    run_data = _load_run(run_id)

    # Delete the file
    file_path = _run_file_path(run_id)
    file_path.unlink()

    # Update index
    _update_index_for_run(run_data, operation="remove")


@router.get(
    "/{run_id}/compare/{other_id}",
    response_model=RunCompareResponse,
    summary="Compare two runs",
    description="Compares two runs showing differences in metrics and output vs ground truth.",
)
async def compare_runs(run_id: str, other_id: str) -> RunCompareResponse:
    """Compare two runs.

    Args:
        run_id: First run ID
        other_id: Second run ID

    Returns:
        RunCompareResponse with detailed comparison

    Raises:
        HTTPException: 404 if either run not found
    """
    # Load both runs
    run_a_data = _load_run(run_id)
    run_b_data = _load_run(other_id)

    # Build comparison objects
    run_a = RunComparison(
        run_id=run_id,
        prompt_id=run_a_data["prompt_id"],
        config_id=run_a_data["config_id"],
        document_name=run_a_data["document_name"],
        status=run_a_data["status"],
        metrics=run_a_data.get("metrics"),
    )

    run_b = RunComparison(
        run_id=other_id,
        prompt_id=run_b_data["prompt_id"],
        config_id=run_b_data["config_id"],
        document_name=run_b_data["document_name"],
        status=run_b_data["status"],
        metrics=run_b_data.get("metrics"),
    )

    # Compare metrics
    metric_comparisons = _compare_metrics(
        run_a_data.get("metrics"),
        run_b_data.get("metrics"),
    )

    # Compare outputs
    field_differences = _compare_outputs(
        run_a_data.get("output"),
        run_b_data.get("output"),
    )

    # Create summary
    summary = _create_comparison_summary(
        run_a_data,
        run_b_data,
        metric_comparisons,
        field_differences,
    )

    return RunCompareResponse(
        run_a=run_a,
        run_b=run_b,
        metric_comparisons=metric_comparisons,
        field_differences=field_differences,
        summary=summary,
    )
