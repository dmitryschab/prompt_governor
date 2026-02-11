"""Run execution data models."""

from datetime import datetime
from typing import Dict, Optional
from uuid import UUID, uuid4

from pydantic import BaseModel, Field, field_validator


class Run(BaseModel):
    """Represents a single prompt execution run.

    Run tracks the execution of a prompt with a specific configuration
    against a document, including status, output, and metrics.
    """

    id: UUID = Field(
        default_factory=uuid4, description="Unique identifier for this run"
    )
    prompt_id: UUID = Field(..., description="ID of the prompt version used")
    config_id: UUID = Field(..., description="ID of the model configuration used")
    document_name: str = Field(..., description="Name of the document being processed")
    status: str = Field(
        default="pending",
        description="Current status of the run",
        pattern="^(pending|running|completed|failed)$",
    )
    started_at: datetime = Field(
        default_factory=datetime.utcnow, description="When the run started"
    )
    completed_at: Optional[datetime] = Field(
        None, description="When the run completed (if finished)"
    )
    output: Optional[Dict] = Field(None, description="The generated output/result")
    metrics: Optional[Dict] = Field(
        None, description="Performance metrics (latency, tokens, etc.)"
    )
    cost_usd: Optional[float] = Field(
        None, ge=0.0, description="Cost of this run in USD"
    )
    tokens: Optional[Dict] = Field(
        None, description="Token usage stats with 'input' and 'output' keys"
    )

    @field_validator("status")
    @classmethod
    def validate_status(cls, v: str) -> str:
        """Validate status is one of the allowed values."""
        allowed = ("pending", "running", "completed", "failed")
        if v not in allowed:
            raise ValueError(f"status must be one of: {', '.join(allowed)}")
        return v

    @field_validator("completed_at")
    @classmethod
    def validate_completion(cls, v: Optional[datetime], info) -> Optional[datetime]:
        """Validate that completed_at is after started_at if both exist."""
        if v is not None:
            started = info.data.get("started_at")
            if started is not None and v < started:
                raise ValueError("completed_at must be after started_at")
        return v

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "id": "c3d4e5f6-a7b8-9012-cdef-345678901234",
                    "prompt_id": "12345678-1234-1234-1234-123456789abc",
                    "config_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
                    "document_name": "annual_report_2023.pdf",
                    "status": "completed",
                    "started_at": "2024-01-15T10:30:00Z",
                    "completed_at": "2024-01-15T10:30:05Z",
                    "output": {
                        "summary": "The company reported strong growth...",
                        "key_points": ["Revenue up 25%", "New markets entered"],
                    },
                    "metrics": {"latency_ms": 5234, "tokens_per_second": 45.2},
                    "cost_usd": 0.045,
                    "tokens": {"input": 2048, "output": 512},
                },
                {
                    "id": "d4e5f6a7-b8c9-0123-defa-456789012345",
                    "prompt_id": "12345678-1234-1234-1234-123456789abc",
                    "config_id": "b2c3d4e5-f6a7-8901-bcde-f23456789012",
                    "document_name": "contract_draft_v2.docx",
                    "status": "running",
                    "started_at": "2024-01-15T11:00:00Z",
                    "completed_at": None,
                    "output": None,
                    "metrics": None,
                    "cost_usd": None,
                    "tokens": None,
                },
            ]
        }
    }
