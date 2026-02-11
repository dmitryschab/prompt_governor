"""File-based JSON storage utilities for prompt governor.

This module provides utilities for reading, writing, and managing JSON files
in the data directory structure. It handles:
- JSON file I/O with proper formatting
- Directory and file listing operations
- UUID generation for unique identifiers
- Collection management for prompts, configs, and runs
"""

import json
import os
import uuid
from pathlib import Path
from typing import Any

# Base data directory
DATA_DIR = Path(__file__).parent.parent.parent / "data"

# Valid collections
COLLECTIONS = {"prompts", "configs", "runs"}


def load_json(filepath: str | Path) -> Any:
    """Read and parse a JSON file.

    Args:
        filepath: Path to the JSON file to read.

    Returns:
        The parsed JSON data (dict, list, etc.).

    Raises:
        FileNotFoundError: If the file does not exist.
        json.JSONDecodeError: If the file contains invalid JSON.
        PermissionError: If the file cannot be read.
    """
    filepath = Path(filepath)

    if not filepath.exists():
        raise FileNotFoundError(f"JSON file not found: {filepath}")

    with open(filepath, "r", encoding="utf-8") as f:
        return json.load(f)


def save_json(filepath: str | Path, data: Any, indent: int = 2) -> None:
    """Write data to a JSON file with formatting.

    Creates parent directories if they don't exist.

    Args:
        filepath: Path where to write the JSON file.
        data: The data to serialize to JSON.
        indent: Number of spaces for indentation (default: 2).

    Raises:
        PermissionError: If the file cannot be written.
        TypeError: If data cannot be serialized to JSON.
    """
    filepath = Path(filepath)

    # Ensure parent directory exists
    filepath.parent.mkdir(parents=True, exist_ok=True)

    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=indent, ensure_ascii=False)
        f.write("\n")  # Trailing newline for POSIX compliance


def list_files(directory: str | Path, pattern: str = "*.json") -> list[str]:
    """List files in a directory matching a glob pattern.

    Args:
        directory: Path to the directory to search.
        pattern: Glob pattern for file matching (default: "*.json").

    Returns:
        List of matching filenames (sorted alphabetically).

    Raises:
        FileNotFoundError: If the directory does not exist.
    """
    directory = Path(directory)

    if not directory.exists():
        raise FileNotFoundError(f"Directory not found: {directory}")

    if not directory.is_dir():
        raise NotADirectoryError(f"Path is not a directory: {directory}")

    files = sorted([f.name for f in directory.glob(pattern) if f.is_file()])
    return files


def generate_id() -> str:
    """Generate a UUID v4 string for unique identifiers.

    Returns:
        A UUID v4 string without dashes (32 hex characters).
    """
    return uuid.uuid4().hex


def get_collection_path(collection_name: str) -> Path:
    """Get the filesystem path for a collection.

    Args:
        collection_name: Name of the collection (prompts, configs, or runs).

    Returns:
        Path object pointing to the collection directory.

    Raises:
        ValueError: If collection_name is not a valid collection.
    """
    if collection_name not in COLLECTIONS:
        raise ValueError(
            f"Invalid collection: '{collection_name}'. "
            f"Must be one of: {', '.join(sorted(COLLECTIONS))}"
        )

    return DATA_DIR / collection_name


def load_index(collection_name: str) -> dict[str, Any]:
    """Load the index file for a collection.

    Args:
        collection_name: Name of the collection (prompts, configs, or runs).

    Returns:
        Dictionary containing the index data.
        Returns empty dict if index file doesn't exist.

    Raises:
        ValueError: If collection_name is not a valid collection.
        json.JSONDecodeError: If index file contains invalid JSON.
    """
    collection_path = get_collection_path(collection_name)
    index_path = collection_path / "index.json"

    try:
        return load_json(index_path)
    except FileNotFoundError:
        # Return empty index if file doesn't exist
        return {"items": [], "version": 1}


def save_index(collection_name: str, data: dict[str, Any]) -> None:
    """Save the index file for a collection.

    Args:
        collection_name: Name of the collection (prompts, configs, or runs).
        data: Dictionary to save as the index.

    Raises:
        ValueError: If collection_name is not a valid collection.
        PermissionError: If the file cannot be written.
    """
    collection_path = get_collection_path(collection_name)
    index_path = collection_path / "index.json"

    save_json(index_path, data)


# Backward compatibility alias
get_collection_dir = get_collection_path
