"""Prompt version data models."""

from datetime import datetime
from typing import Dict, List, Optional
from uuid import uuid4

from pydantic import BaseModel, Field


def generate_uuid_hex() -> str:
    """Generate a UUID v4 in hex format (no dashes)."""
    return uuid4().hex


class PromptBlock(BaseModel):
    """A single block within a prompt version.

    Contains the title, body text, and optional comment for this block.
    """

    title: str = Field(..., description="Title of the prompt block")
    body: str = Field(..., description="Main content/body of the prompt block")
    comment: Optional[str] = Field(
        None, description="Optional comment about this block"
    )


class PromptVersion(BaseModel):
    """A version of a prompt with its content and metadata.

    PromptVersion represents a snapshot of a prompt at a specific point in time.
    It contains the structured prompt blocks and metadata for tracking versions.
    """

    id: str = Field(
        default_factory=generate_uuid_hex,
        description="Unique identifier for this prompt version (hex format, no dashes)",
    )
    name: str = Field(..., description="Name of the prompt")
    description: Optional[str] = Field(
        None, description="Optional description of the prompt"
    )
    blocks: List[PromptBlock] = Field(
        default_factory=list, description="List of prompt blocks"
    )
    created_at: datetime = Field(
        default_factory=datetime.utcnow, description="When this version was created"
    )
    parent_id: Optional[str] = Field(
        None,
        description="ID of the parent version if this is a fork (hex format, no dashes)",
    )
    tags: List[str] = Field(
        default_factory=list, description="Tags for categorizing this prompt"
    )

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "id": "12345678-1234-1234-1234-123456789abc",
                    "name": "Document Summarizer",
                    "description": "Summarizes long documents into key points",
                    "blocks": [
                        {
                            "title": "System Instruction",
                            "body": "You are a helpful assistant that summarizes documents.",
                            "comment": "Sets the role and behavior",
                        },
                        {
                            "title": "User Prompt",
                            "body": "Please summarize the following document:\n\n{document}",
                            "comment": "Main user prompt with placeholder",
                        },
                    ],
                    "created_at": "2024-01-15T10:30:00Z",
                    "parent_id": None,
                    "tags": ["summarization", "document-processing"],
                }
            ]
        }
    }
