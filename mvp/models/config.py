"""Model configuration data models."""

from datetime import datetime
from typing import Dict, Optional
from uuid import uuid4

from pydantic import BaseModel, Field, field_validator


def generate_uuid_hex() -> str:
    """Generate a UUID v4 in hex format (no dashes)."""
    return uuid4().hex


class ModelConfig(BaseModel):
    """Configuration for an AI model provider and its parameters.

    ModelConfig defines which model to use (e.g., GPT-4, Claude) and how to
    configure it (temperature, max tokens, etc.).
    """

    id: str = Field(
        default_factory=generate_uuid_hex,
        description="Unique identifier for this configuration (hex format, no dashes)",
    )
    name: str = Field(..., description="Human-readable name for this configuration")
    provider: str = Field(
        ...,
        description="AI provider (openai, anthropic, openrouter)",
        pattern="^(openai|anthropic|openrouter)$",
    )
    model_id: str = Field(
        ..., description="Specific model identifier (e.g., 'gpt-4', 'claude-3-opus')"
    )
    reasoning_effort: Optional[str] = Field(
        None,
        description="Reasoning effort level (low, medium, high) for supported models",
    )
    temperature: float = Field(
        default=0.7,
        ge=0.0,
        le=2.0,
        description="Sampling temperature (0.0-2.0, lower = more deterministic)",
    )
    max_tokens: Optional[int] = Field(
        None, ge=1, description="Maximum tokens to generate"
    )
    extra_params: Dict = Field(
        default_factory=dict, description="Additional provider-specific parameters"
    )
    created_at: datetime = Field(
        default_factory=datetime.utcnow, description="When this config was created"
    )

    @field_validator("reasoning_effort")
    @classmethod
    def validate_reasoning_effort(cls, v: Optional[str]) -> Optional[str]:
        """Validate reasoning_effort is one of the allowed values."""
        if v is not None and v not in ("low", "medium", "high"):
            raise ValueError("reasoning_effort must be 'low', 'medium', or 'high'")
        return v

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
                    "name": "GPT-4 Creative",
                    "provider": "openai",
                    "model_id": "gpt-4-turbo-preview",
                    "reasoning_effort": "medium",
                    "temperature": 0.8,
                    "max_tokens": 4096,
                    "extra_params": {"top_p": 0.95, "frequency_penalty": 0.0},
                    "created_at": "2024-01-15T10:30:00Z",
                },
                {
                    "id": "b2c3d4e5-f6a7-8901-bcde-f23456789012",
                    "name": "Claude Precise",
                    "provider": "anthropic",
                    "model_id": "claude-3-opus-20240229",
                    "reasoning_effort": None,
                    "temperature": 0.1,
                    "max_tokens": 8192,
                    "extra_params": {},
                    "created_at": "2024-01-15T11:00:00Z",
                },
            ]
        }
    }
