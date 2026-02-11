"""Documents API endpoints for listing and managing documents.

This module provides FastAPI endpoints for:
- Listing available documents in the documents directory
- Getting document metadata (size, type, modified time)
- Filtering by file extension
"""

import os
from datetime import datetime
from pathlib import Path
from typing import List, Literal, Optional

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

router = APIRouter(
    prefix="/api/documents",
    tags=["documents"],
    responses={404: {"description": "Document not found"}},
)

# Configuration: Path to documents directory
# In Docker container, this will be /app/documents/
DOCUMENTS_PATH = Path(os.environ.get("DOCUMENTS_PATH", "/app/documents"))


class DocumentInfo(BaseModel):
    """Model representing document metadata."""

    name: str = Field(..., description="Filename of the document")
    size: int = Field(..., description="File size in bytes")
    type: Literal["pdf", "text"] = Field(..., description="Document type (pdf or text)")
    extension: str = Field(..., description="File extension")
    modified_at: datetime = Field(..., description="Last modification timestamp")

    class Config:
        """Pydantic configuration."""

        json_schema_extra = {
            "example": {
                "name": "contract.pdf",
                "size": 102400,
                "type": "pdf",
                "extension": ".pdf",
                "modified_at": "2026-02-11T10:30:00",
            }
        }


class DocumentListResponse(BaseModel):
    """Response model for listing documents."""

    documents: List[DocumentInfo] = Field(
        ..., description="List of available documents"
    )
    total: int = Field(..., description="Total number of documents")

    class Config:
        """Pydantic configuration."""

        json_schema_extra = {
            "example": {
                "documents": [
                    {
                        "name": "contract.pdf",
                        "size": 102400,
                        "type": "pdf",
                        "extension": ".pdf",
                        "modified_at": "2026-02-11T10:30:00",
                    }
                ],
                "total": 1,
            }
        }


def _get_document_type(extension: str) -> Literal["pdf", "text"]:
    """Determine document type from file extension.

    Args:
        extension: File extension (including the dot, e.g., '.pdf')

    Returns:
        Either 'pdf' or 'text'

    Raises:
        ValueError: If extension is not supported
    """
    ext = extension.lower()
    if ext == ".pdf":
        return "pdf"
    elif ext in (".txt", ".text"):
        return "text"
    else:
        raise ValueError(f"Unsupported file extension: {extension}")


def _get_file_info(file_path: Path) -> DocumentInfo:
    """Extract metadata from a file.

    Args:
        file_path: Path to the file

    Returns:
        DocumentInfo with metadata
    """
    stat = file_path.stat()
    extension = file_path.suffix

    return DocumentInfo(
        name=file_path.name,
        size=stat.st_size,
        type=_get_document_type(extension),
        extension=extension,
        modified_at=datetime.fromtimestamp(stat.st_mtime),
    )


def _is_supported_file(file_path: Path) -> bool:
    """Check if file has a supported extension.

    Args:
        file_path: Path to check

    Returns:
        True if file is PDF or text
    """
    extension = file_path.suffix.lower()
    return extension in (".pdf", ".txt", ".text")


@router.get(
    "",
    response_model=DocumentListResponse,
    summary="List available documents",
    description="Returns a list of all documents in the documents directory. Supports filtering by file extension.",
)
async def list_documents(
    extension: Optional[str] = Query(
        None,
        description="Filter by file extension (e.g., 'pdf', 'txt', '.pdf', '.txt')",
    ),
) -> DocumentListResponse:
    """List all documents in the documents directory.

    Args:
        extension: Optional file extension filter (with or without leading dot)

    Returns:
        DocumentListResponse containing list of documents

    Raises:
        HTTPException: If documents directory doesn't exist
    """
    # Ensure documents directory exists
    if not DOCUMENTS_PATH.exists():
        raise HTTPException(
            status_code=500, detail=f"Documents directory not found: {DOCUMENTS_PATH}"
        )

    # Collect all supported files
    documents: List[DocumentInfo] = []

    # Normalize extension filter (ensure it starts with a dot)
    if extension:
        ext_filter = extension if extension.startswith(".") else f".{extension}"
        ext_filter = ext_filter.lower()
    else:
        ext_filter = None

    # Scan documents directory
    for file_path in DOCUMENTS_PATH.iterdir():
        # Skip directories and hidden files
        if not file_path.is_file() or file_path.name.startswith("."):
            continue

        # Skip unsupported file types
        if not _is_supported_file(file_path):
            continue

        # Apply extension filter if provided
        if ext_filter and file_path.suffix.lower() != ext_filter:
            continue

        try:
            doc_info = _get_file_info(file_path)
            documents.append(doc_info)
        except (OSError, ValueError) as e:
            # Log error but continue with other files
            # In a production app, you'd want proper logging here
            continue

    # Sort by name for consistent ordering
    documents.sort(key=lambda d: d.name)

    return DocumentListResponse(
        documents=documents,
        total=len(documents),
    )


@router.get(
    "/{name}",
    response_model=DocumentInfo,
    summary="Get document information",
    description="Returns metadata for a specific document by name.",
)
async def get_document(name: str) -> DocumentInfo:
    """Get metadata for a specific document.

    Args:
        name: Name of the document file

    Returns:
        DocumentInfo with file metadata

    Raises:
        HTTPException: 404 if document not found, 400 if unsupported type
    """
    # Validate filename (prevent directory traversal)
    if "/" in name or "\\" in name or ".." in name:
        raise HTTPException(status_code=400, detail="Invalid filename")

    file_path = DOCUMENTS_PATH / name

    # Check if file exists
    if not file_path.exists():
        raise HTTPException(status_code=404, detail=f"Document '{name}' not found")

    # Check if it's a file (not a directory)
    if not file_path.is_file():
        raise HTTPException(status_code=400, detail=f"'{name}' is not a file")

    # Check if file type is supported
    if not _is_supported_file(file_path):
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file type. Only PDF and text files are supported.",
        )

    try:
        return _get_file_info(file_path)
    except (OSError, ValueError) as e:
        raise HTTPException(status_code=500, detail=f"Error reading document: {str(e)}")


@router.head(
    "/{name}",
    summary="Check document existence",
    description="Returns 200 if document exists, 404 if not. Useful for existence checks without transferring data.",
)
async def check_document_exists(name: str):
    """Check if a document exists.

    Args:
        name: Name of the document file

    Returns:
        200 OK if exists, 404 if not found

    Raises:
        HTTPException: 404 if not found, 400 if invalid filename
    """
    # Validate filename
    if "/" in name or "\\" in name or ".." in name:
        raise HTTPException(status_code=400, detail="Invalid filename")

    file_path = DOCUMENTS_PATH / name

    if not file_path.exists() or not file_path.is_file():
        raise HTTPException(status_code=404, detail=f"Document '{name}' not found")

    if not _is_supported_file(file_path):
        raise HTTPException(status_code=404, detail=f"Document '{name}' not found")

    return {"exists": True}
