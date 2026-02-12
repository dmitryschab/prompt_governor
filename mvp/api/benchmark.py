"""Benchmark API endpoints for comparing prompt performance across configurations.

This module provides FastAPI endpoints for:
- Getting aggregated benchmark summaries with overall metrics
- Per-document comparison results
- Field-level accuracy analysis
- Cost and performance tracking
"""

import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Literal, Optional

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field

from mvp.models.responses import ErrorResponse, SuccessResponse
from mvp.services.storage import DATA_DIR, load_json

router = APIRouter(
    prefix="/api/benchmark",
    tags=["benchmark"],
    responses={
        404: {"description": "Benchmark data not found"},
        500: {"description": "Internal server error"},
    },
)

# Path to benchmark summary file
BENCHMARK_SUMMARY_PATH = DATA_DIR / "runs" / "benchmark_summary.json"


# =============================================================================
# Pydantic Models for Benchmark Data (matching actual file format)
# =============================================================================


class CostSummary(BaseModel):
    """Cost summary for a reasoning effort."""

    total_cost_usd: float = Field(..., ge=0.0)
    avg_cost_per_document: float = Field(..., ge=0.0)
    total_prompt_tokens: int = Field(..., ge=0)
    total_completion_tokens: int = Field(..., ge=0)
    total_tokens: int = Field(..., ge=0)
    avg_tokens_per_document: float = Field(..., ge=0.0)


class LatencySummary(BaseModel):
    """Latency summary for a reasoning effort."""

    total_latency_s: float = Field(..., ge=0.0)
    avg_latency_s: float = Field(..., ge=0.0)
    min_latency_s: float = Field(..., ge=0.0)
    max_latency_s: float = Field(..., ge=0.0)


class DocumentAccuracy(BaseModel):
    """Accuracy metrics for a single document."""

    structure_f1: Optional[float] = Field(None, ge=0.0, le=1.0)
    value_f1: Optional[float] = Field(None, ge=0.0, le=1.0)
    list_f1: Optional[float] = Field(None, ge=0.0, le=1.0)
    weighted_f1: Optional[float] = Field(None, ge=0.0, le=1.0)


class DocumentResult(BaseModel):
    """Result for a single document in benchmark."""

    document_name: str
    success: bool
    cache_hit: bool
    latency_s: float
    cost_usd: float
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int
    accuracy: DocumentAccuracy


class OverallMetrics(BaseModel):
    """Overall metrics for a reasoning effort."""

    field_accuracy: float = Field(..., ge=0.0, le=100.0)
    avg_structure_f1: float = Field(..., ge=0.0, le=1.0)
    avg_value_f1: float = Field(..., ge=0.0, le=1.0)
    avg_list_f1: float = Field(..., ge=0.0, le=1.0)
    avg_weighted_f1: float = Field(..., ge=0.0, le=1.0)
    total_documents: int = Field(..., ge=0)
    successful_documents: int = Field(..., ge=0)
    success_rate: float = Field(..., ge=0.0, le=100.0)
    cache_hits: int = Field(..., ge=0)
    cache_hit_rate: float = Field(..., ge=0.0, le=100.0)


class ReasoningEffortData(BaseModel):
    """Complete data for a reasoning effort level."""

    config_id: str
    config_name: str
    template: str
    mode: str
    metrics: Dict[
        str, Any
    ]  # Contains overall, cost_summary, latency_summary, documents


class ComparisonMetrics(BaseModel):
    """Comparison metrics between reasoning efforts."""

    accuracy_difference: Dict[str, float]
    cost_difference: Dict[str, float]
    latency_difference: Dict[str, float]
    winner: str


class BenchmarkSummary(BaseModel):
    """Complete benchmark summary structure."""

    id: str
    name: str
    description: str
    created_at: str
    model: str
    reasoning_efforts: Dict[str, ReasoningEffortData]
    document_count: int
    document_names: List[str]
    comparison: Dict[str, Any]


# =============================================================================
# Aggregated Response Models (for API responses)
# =============================================================================


class ReasoningEffortMetrics(BaseModel):
    """Simplified metrics for a reasoning effort level."""

    effort: Literal["minimal", "low", "medium", "high"]
    config_name: str
    mode: str
    field_accuracy: float
    avg_weighted_f1: float
    avg_structure_f1: float
    avg_value_f1: float
    total_cost_usd: float
    avg_cost_per_document: float
    total_latency_s: float
    avg_latency_s: float
    total_tokens: int
    total_documents: int
    successful_documents: int
    success_rate: float


class CostPerformanceSummary(BaseModel):
    """Cost and performance summary statistics."""

    total_cost_usd: float
    avg_cost_per_document: float
    total_latency_s: float
    avg_latency_s: float
    total_tokens_consumed: Dict[str, int]


class BenchmarkSummaryResponse(BaseModel):
    """Aggregated benchmark summary for API response."""

    id: str
    name: str
    model: str
    created_at: str
    total_documents: int
    reasoning_efforts: List[ReasoningEffortMetrics]
    cost_performance: CostPerformanceSummary
    comparison: Dict[str, Any]


class DocumentDetail(BaseModel):
    """Detailed document info with cross-effort comparison."""

    document_name: str
    results: Dict[str, Any]  # Results per reasoning effort
    best_effort: Optional[str]
    best_weighted_f1: Optional[float]


class DocumentsResponse(BaseModel):
    """Response for document-level benchmark data."""

    documents: List[DocumentDetail]
    total_documents: int


class FieldAccuracyItem(BaseModel):
    """Field-level accuracy for a single field across documents."""

    field_name: str
    reasoning_effort: str
    present_in_ground_truth: int
    correctly_extracted: int
    accuracy_pct: float


class FieldsResponse(BaseModel):
    """Response for field-level accuracy data."""

    fields: List[FieldAccuracyItem]
    total_fields: int
    by_reasoning_effort: Dict[str, List[FieldAccuracyItem]]


# =============================================================================
# Helper Functions
# =============================================================================


def _load_benchmark_data() -> Optional[Dict[str, Any]]:
    """Load benchmark summary data from file.

    Returns:
        Benchmark data dictionary or None if file doesn't exist

    Raises:
        HTTPException: If file exists but is corrupted
    """
    if not BENCHMARK_SUMMARY_PATH.exists():
        return None

    try:
        return load_json(BENCHMARK_SUMMARY_PATH)
    except (json.JSONDecodeError, ValueError) as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Benchmark data file is corrupted: {str(e)}",
        )


def _aggregate_reasoning_efforts(data: Dict[str, Any]) -> List[ReasoningEffortMetrics]:
    """Aggregate reasoning effort metrics for API response.

    Args:
        data: Raw benchmark data

    Returns:
        List of aggregated reasoning effort metrics
    """
    efforts = []
    reasoning_efforts = data.get("reasoning_efforts", {})

    for effort_key, effort_data in reasoning_efforts.items():
        metrics = effort_data.get("metrics", {})
        overall = metrics.get("overall", {})
        cost_summary = metrics.get("cost_summary", {})
        latency_summary = metrics.get("latency_summary", {})

        efforts.append(
            ReasoningEffortMetrics(
                effort=effort_key,
                config_name=effort_data.get("config_name", effort_key),
                mode=effort_data.get("mode", "unknown"),
                field_accuracy=overall.get("field_accuracy", 0.0),
                avg_weighted_f1=overall.get("avg_weighted_f1", 0.0),
                avg_structure_f1=overall.get("avg_structure_f1", 0.0),
                avg_value_f1=overall.get("avg_value_f1", 0.0),
                total_cost_usd=cost_summary.get("total_cost_usd", 0.0),
                avg_cost_per_document=cost_summary.get("avg_cost_per_document", 0.0),
                total_latency_s=latency_summary.get("total_latency_s", 0.0),
                avg_latency_s=latency_summary.get("avg_latency_s", 0.0),
                total_tokens=cost_summary.get("total_tokens", 0),
                total_documents=overall.get("total_documents", 0),
                successful_documents=overall.get("successful_documents", 0),
                success_rate=overall.get("success_rate", 0.0),
            )
        )

    return efforts


def _aggregate_cost_performance(data: Dict[str, Any]) -> CostPerformanceSummary:
    """Aggregate cost and performance across all efforts.

    Args:
        data: Raw benchmark data

    Returns:
        Aggregated cost and performance summary
    """
    total_cost = 0.0
    total_latency = 0.0
    total_tokens_input = 0
    total_tokens_output = 0

    reasoning_efforts = data.get("reasoning_efforts", {})

    for effort_data in reasoning_efforts.values():
        metrics = effort_data.get("metrics", {})
        cost_summary = metrics.get("cost_summary", {})
        latency_summary = metrics.get("latency_summary", {})

        total_cost += cost_summary.get("total_cost_usd", 0.0)
        total_latency += latency_summary.get("total_latency_s", 0.0)
        total_tokens_input += cost_summary.get("total_prompt_tokens", 0)
        total_tokens_output += cost_summary.get("total_completion_tokens", 0)

    document_count = data.get("document_count", 1)

    return CostPerformanceSummary(
        total_cost_usd=round(total_cost, 4),
        avg_cost_per_document=round(total_cost / document_count, 6)
        if document_count > 0
        else 0.0,
        total_latency_s=round(total_latency, 2),
        avg_latency_s=round(total_latency / document_count, 2)
        if document_count > 0
        else 0.0,
        total_tokens_consumed={
            "input": total_tokens_input,
            "output": total_tokens_output,
            "total": total_tokens_input + total_tokens_output,
        },
    )


def _extract_document_details(data: Dict[str, Any]) -> List[DocumentDetail]:
    """Extract per-document details from benchmark data.

    Args:
        data: Raw benchmark data

    Returns:
        List of document details
    """
    document_names = data.get("document_names", [])
    reasoning_efforts = data.get("reasoning_efforts", {})
    documents = []

    for doc_name in document_names:
        doc_results = {}
        best_effort = None
        best_f1 = -1.0

        for effort_key, effort_data in reasoning_efforts.items():
            metrics = effort_data.get("metrics", {})
            docs = metrics.get("documents", [])

            # Find this document in the documents list
            for doc in docs:
                if doc.get("document_name") == doc_name:
                    doc_results[effort_key] = doc

                    # Track best weighted F1
                    accuracy = doc.get("accuracy", {})
                    weighted_f1 = accuracy.get("weighted_f1")
                    if weighted_f1 is not None and weighted_f1 > best_f1:
                        best_f1 = weighted_f1
                        best_effort = effort_key
                    break

        documents.append(
            DocumentDetail(
                document_name=doc_name,
                results=doc_results,
                best_effort=best_effort,
                best_weighted_f1=best_f1 if best_f1 >= 0 else None,
            )
        )

    return documents


def _extract_field_accuracy(data: Dict[str, Any]) -> FieldsResponse:
    """Extract field-level accuracy from benchmark data.

    Note: Field-level accuracy requires detailed field comparison data
    that may not be in the summary. Returns available data.

    Args:
        data: Raw benchmark data

    Returns:
        Fields response with available field data
    """
    # Field-level accuracy data is typically in per-field comparison files
    # This is a simplified version based on available data
    fields = []
    by_effort = {}

    reasoning_efforts = data.get("reasoning_efforts", {})

    for effort_key, effort_data in reasoning_efforts.items():
        # Create synthetic field accuracy from overall metrics
        overall = effort_data.get("metrics", {}).get("overall", {})
        field_accuracy = overall.get("field_accuracy", 0.0)

        # Create a summary field entry
        field_entry = FieldAccuracyItem(
            field_name="overall_fields",
            reasoning_effort=effort_key,
            present_in_ground_truth=overall.get("total_documents", 0),
            correctly_extracted=overall.get("successful_documents", 0),
            accuracy_pct=field_accuracy,
        )

        fields.append(field_entry)
        by_effort[effort_key] = [field_entry]

    return FieldsResponse(
        fields=fields,
        total_fields=len(fields),
        by_reasoning_effort=by_effort,
    )


def _generate_placeholder_summary() -> Dict[str, Any]:
    """Generate placeholder benchmark summary with instructions."""
    return {
        "status": "placeholder",
        "message": "No benchmark data available",
        "generated_at": datetime.utcnow().isoformat() + "Z",
        "instructions": {
            "title": "How to Generate Benchmark Data",
            "steps": [
                "1. Ensure you have documents in the documents/ directory",
                "2. Ensure you have corresponding ground truth files in ground_truth/",
                "3. Create prompt configurations for different reasoning efforts",
                "4. Run the benchmark pipeline to generate benchmark_summary.json",
                "5. The file should be saved to data/runs/benchmark_summary.json",
            ],
            "api_usage": {
                "create_configs": "POST /api/configs - Create configs with reasoning_effort: 'minimal', 'low'",
                "create_runs": "POST /api/runs - Execute runs against documents",
                "compare": "GET /api/runs/{id}/compare/{other_id} - Compare results",
            },
        },
    }


def _generate_placeholder_documents() -> Dict[str, Any]:
    """Generate placeholder documents response with instructions."""
    return {
        "status": "placeholder",
        "message": "No document benchmark data available",
        "documents": [],
        "total_documents": 0,
        "instructions": {
            "title": "How to Generate Per-Document Benchmark Data",
            "steps": [
                "1. Add documents to the documents/ directory",
                "2. Add corresponding ground truth JSON files to ground_truth/",
                "3. Create runs using POST /api/runs for each document",
                "4. Compare runs using GET /api/runs/{id}/compare/{other_id}",
            ],
        },
    }


def _generate_placeholder_fields() -> Dict[str, Any]:
    """Generate placeholder fields response with instructions."""
    return {
        "status": "placeholder",
        "message": "No field-level accuracy data available",
        "fields": [],
        "total_fields": 0,
        "instructions": {
            "title": "How to Generate Field-Level Accuracy Data",
            "steps": [
                "1. Execute runs against documents with ground truth",
                "2. The system automatically calculates field-level metrics",
                "3. Metrics include: structure_f1, value_f1, weighted_f1",
                "4. Run the benchmark aggregation to populate this endpoint",
            ],
        },
    }


# =============================================================================
# API Endpoints
# =============================================================================


@router.get(
    "/summary",
    response_model=SuccessResponse,
    summary="Get benchmark summary",
    description="Returns aggregated benchmark data including overall metrics for each reasoning effort (minimal, low), cost and performance summaries, and cross-effort comparisons.",
    responses={
        200: {
            "description": "Benchmark summary data",
            "content": {
                "application/json": {
                    "example": {
                        "success": True,
                        "data": {
                            "id": "benchmark-summary-gpt5-mini",
                            "name": "GPT-5-mini Benchmark Summary",
                            "model": "gpt-5-mini",
                            "total_documents": 8,
                            "reasoning_efforts": [
                                {
                                    "effort": "minimal",
                                    "config_name": "GPT-5-mini (minimal)",
                                    "mode": "monolith",
                                    "field_accuracy": 70.83,
                                    "avg_weighted_f1": 0.362,
                                    "avg_structure_f1": 0.869,
                                    "avg_value_f1": 0.203,
                                    "total_cost_usd": 0.2411,
                                    "avg_cost_per_document": 0.030139,
                                    "total_latency_s": 142.95,
                                    "avg_latency_s": 17.87,
                                    "total_tokens": 579950,
                                    "total_documents": 8,
                                    "successful_documents": 8,
                                    "success_rate": 100.0,
                                }
                            ],
                            "cost_performance": {
                                "total_cost_usd": 0.4822,
                                "avg_cost_per_document": 0.0603,
                                "total_latency_s": 285.9,
                                "avg_latency_s": 35.74,
                                "total_tokens_consumed": {
                                    "input": 1144680,
                                    "output": 15220,
                                    "total": 1159900,
                                },
                            },
                            "comparison": {
                                "accuracy_difference": {"structure_f1": 0.0},
                                "cost_difference": {"total_cost_usd": 0.0},
                                "winner": "minimal",
                            },
                        },
                    }
                }
            },
        },
        500: {"model": ErrorResponse},
    },
)
async def get_benchmark_summary() -> SuccessResponse:
    """Get aggregated benchmark summary.

    Returns comprehensive benchmark data including:
    - Metrics for each reasoning effort (minimal, low, medium, high)
    - Cost and performance summaries
    - Cross-effort comparisons

    If no benchmark data exists, returns placeholder data with instructions
    on how to generate it.

    Returns:
        SuccessResponse with BenchmarkSummaryResponse or placeholder instructions

    Raises:
        HTTPException: 500 if data file exists but is corrupted
    """
    data = _load_benchmark_data()

    if data is None:
        # Return placeholder with instructions
        placeholder = _generate_placeholder_summary()
        return SuccessResponse(
            success=True,
            data=placeholder,
            message="Benchmark data not found. See instructions in response data.",
        )

    try:
        # Aggregate data for response
        efforts = _aggregate_reasoning_efforts(data)
        cost_perf = _aggregate_cost_performance(data)

        response_data = BenchmarkSummaryResponse(
            id=data.get("id", "unknown"),
            name=data.get("name", "Benchmark Summary"),
            model=data.get("model", "unknown"),
            created_at=data.get("created_at", datetime.utcnow().isoformat()),
            total_documents=data.get("document_count", 0),
            reasoning_efforts=efforts,
            cost_performance=cost_perf,
            comparison=data.get("comparison", {}),
        )

        return SuccessResponse(success=True, data=response_data.model_dump())
    except Exception as e:
        # If validation fails, return error with helpful message
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to parse benchmark data: {str(e)}",
        )


@router.get(
    "/documents",
    response_model=SuccessResponse,
    summary="Get per-document benchmark results",
    description="Returns detailed per-document results showing how each document performed across different reasoning efforts.",
    responses={
        200: {
            "description": "Per-document benchmark data",
            "content": {
                "application/json": {
                    "example": {
                        "success": True,
                        "data": {
                            "documents": [
                                {
                                    "document_name": "contract.pdf",
                                    "results": {
                                        "minimal": {
                                            "success": True,
                                            "accuracy": {"weighted_f1": 0.362},
                                        }
                                    },
                                    "best_effort": "minimal",
                                    "best_weighted_f1": 0.362,
                                }
                            ],
                            "total_documents": 1,
                        },
                    }
                }
            },
        },
    },
)
async def get_benchmark_documents() -> SuccessResponse:
    """Get detailed per-document benchmark results.

    Returns detailed information for each document including:
    - Document name and results per reasoning effort
    - Best F1 score achieved
    - Which effort produced the best result

    If no benchmark data exists, returns placeholder with instructions.

    Returns:
        SuccessResponse with DocumentsResponse or placeholder
    """
    data = _load_benchmark_data()

    if data is None:
        placeholder = _generate_placeholder_documents()
        return SuccessResponse(
            success=True,
            data=placeholder,
            message="Document benchmark data not found. See instructions.",
        )

    try:
        documents = _extract_document_details(data)

        response = DocumentsResponse(
            documents=documents,
            total_documents=len(documents),
        )
        return SuccessResponse(success=True, data=response.model_dump())
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to parse document data: {str(e)}",
        )


@router.get(
    "/fields",
    response_model=SuccessResponse,
    summary="Get field-level accuracy data",
    description="Returns field-level accuracy data showing extraction accuracy across different reasoning efforts.",
    responses={
        200: {
            "description": "Field-level accuracy data",
            "content": {
                "application/json": {
                    "example": {
                        "success": True,
                        "data": {
                            "fields": [
                                {
                                    "field_name": "overall_fields",
                                    "reasoning_effort": "minimal",
                                    "present_in_ground_truth": 8,
                                    "correctly_extracted": 8,
                                    "accuracy_pct": 70.83,
                                }
                            ],
                            "total_fields": 1,
                            "by_reasoning_effort": {"minimal": []},
                        },
                    }
                }
            },
        },
    },
)
async def get_benchmark_fields() -> SuccessResponse:
    """Get field-level accuracy data.

    Returns field-level accuracy statistics including:
    - Per-field accuracy percentages by reasoning effort
    - Aggregated field data

    If no benchmark data exists, returns placeholder with instructions.

    Returns:
        SuccessResponse with FieldsResponse or placeholder
    """
    data = _load_benchmark_data()

    if data is None:
        placeholder = _generate_placeholder_fields()
        return SuccessResponse(
            success=True,
            data=placeholder,
            message="Field accuracy data not found. See instructions.",
        )

    try:
        response = _extract_field_accuracy(data)
        return SuccessResponse(success=True, data=response.model_dump())
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to parse field data: {str(e)}",
        )


@router.get(
    "/health",
    summary="Benchmark data health check",
    description="Quick endpoint to check if benchmark data is available without loading the full dataset.",
)
async def benchmark_health_check() -> Dict[str, Any]:
    """Check if benchmark data is available.

    Returns:
        Dictionary with status and metadata
    """
    exists = BENCHMARK_SUMMARY_PATH.exists()

    if not exists:
        return {
            "status": "not_found",
            "has_data": False,
            "path": str(BENCHMARK_SUMMARY_PATH),
            "message": "Benchmark data not generated yet",
        }

    try:
        stat = BENCHMARK_SUMMARY_PATH.stat()
        data = load_json(BENCHMARK_SUMMARY_PATH)

        reasoning_efforts = list(data.get("reasoning_efforts", {}).keys())

        return {
            "status": "available",
            "has_data": True,
            "path": str(BENCHMARK_SUMMARY_PATH),
            "size_bytes": stat.st_size,
            "last_modified": datetime.fromtimestamp(stat.st_mtime).isoformat() + "Z",
            "data_summary": {
                "id": data.get("id"),
                "name": data.get("name"),
                "model": data.get("model"),
                "total_documents": data.get("document_count", 0),
                "reasoning_efforts": reasoning_efforts,
                "created_at": data.get("created_at"),
            },
        }
    except Exception as e:
        return {
            "status": "error",
            "has_data": False,
            "path": str(BENCHMARK_SUMMARY_PATH),
            "error": str(e),
            "message": "Benchmark data file exists but cannot be read",
        }
