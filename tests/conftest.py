"""Pytest configuration and fixtures for API tests.

This module provides:
- Test client fixture with isolated temporary data directories
- Sample data fixtures for prompts, configs, documents, and runs
- Mock utilities for external dependencies
"""

import json
import os
import shutil
import sys
import tempfile
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Generator
from unittest.mock import MagicMock, patch

import pytest

# =============================================================================
# Test Client Fixture
# =============================================================================


@pytest.fixture
def test_data_dir() -> Generator[Path, None, None]:
    """Create a temporary data directory for testing.

    Yields:
        Path to the temporary data directory
    """
    temp_dir = Path(tempfile.mkdtemp(prefix="prompt_governor_test_"))
    data_dir = temp_dir / "data"
    data_dir.mkdir(parents=True)

    # Create collection directories with empty indexes
    for collection in ["prompts", "configs", "runs"]:
        (data_dir / collection).mkdir(parents=True)
        # Initialize empty index
        with open(data_dir / collection / "index.json", "w") as f:
            json.dump({"items": [], "version": 1}, f)

    yield data_dir

    # Cleanup
    shutil.rmtree(temp_dir, ignore_errors=True)


@pytest.fixture
def documents_dir() -> Generator[Path, None, None]:
    """Create a temporary documents directory with test files.

    Yields:
        Path to the temporary documents directory
    """
    temp_dir = Path(tempfile.mkdtemp(prefix="prompt_governor_docs_"))

    # Create test documents
    (temp_dir / "contract_001.pdf").write_text("Test PDF content 1")
    (temp_dir / "contract_002.pdf").write_text("Test PDF content 2")
    (temp_dir / "report_2024.txt").write_text("Test text content")
    (temp_dir / "notes.text").write_text("Test text content 2")

    yield temp_dir

    # Cleanup
    shutil.rmtree(temp_dir, ignore_errors=True)


@pytest.fixture
def client(
    test_data_dir: Path, documents_dir: Path
) -> Generator["TestClient", None, None]:
    """Create a test client with isolated data directories.

    Args:
        test_data_dir: Fixture providing temporary data directory
        documents_dir: Fixture providing temporary documents directory

    Yields:
        Configured TestClient instance
    """
    from fastapi.testclient import TestClient

    # Documents should be at the same level as data/ (parent of data/)
    root_dir = test_data_dir.parent
    actual_docs_dir = root_dir / "documents"
    actual_docs_dir.mkdir(parents=True, exist_ok=True)

    # Copy test documents to the expected location
    for doc_file in documents_dir.iterdir():
        if doc_file.is_file():
            shutil.copy2(doc_file, actual_docs_dir / doc_file.name)

    # Create a mock storage module with our test paths
    import mvp.services.storage as storage_module

    # Save original values
    original_data_dir = storage_module.DATA_DIR

    # Set test paths
    storage_module.DATA_DIR = test_data_dir

    # Also need to patch documents path in the documents module
    import mvp.api.documents as documents_module

    original_docs_path = documents_module.DOCUMENTS_PATH
    documents_module.DOCUMENTS_PATH = actual_docs_dir

    # Now import and create the app
    from mvp.main import app

    with TestClient(app) as test_client:
        yield test_client

    # Restore original values
    storage_module.DATA_DIR = original_data_dir
    documents_module.DOCUMENTS_PATH = original_docs_path


# =============================================================================
# Sample Data Fixtures
# =============================================================================


@pytest.fixture
def sample_prompt_id(client: "TestClient") -> str:
    """Create and return a sample prompt ID.

    Args:
        client: TestClient fixture

    Returns:
        ID of the created prompt
    """
    prompt_data = {
        "name": "Test Contract Extractor",
        "description": "Extracts key fields from insurance contracts",
        "blocks": [
            {
                "title": "System",
                "body": "You are a helpful assistant.",
                "comment": "System prompt",
            },
            {
                "title": "User",
                "body": "Extract fields from:\\n{document}",
                "comment": "User prompt",
            },
        ],
        "tags": ["extraction", "contracts", "test"],
    }

    response = client.post("/api/prompts", json=prompt_data)
    assert response.status_code == 201, f"Failed to create prompt: {response.text}"
    return response.json()["id"]


@pytest.fixture
def sample_prompt_with_parent(client: "TestClient", sample_prompt_id: str) -> str:
    """Create a sample prompt with a parent (forked version).

    Args:
        client: TestClient fixture
        sample_prompt_id: ID of parent prompt

    Returns:
        ID of the created child prompt
    """
    prompt_data = {
        "name": "Test Contract Extractor v2",
        "description": "Improved version with better extraction",
        "blocks": [
            {
                "title": "System",
                "body": "You are an expert assistant.",
                "comment": "Enhanced system prompt",
            }
        ],
        "parent_id": sample_prompt_id,
        "tags": ["extraction", "contracts", "v2"],
    }

    response = client.post("/api/prompts", json=prompt_data)
    assert response.status_code == 201
    return response.json()["id"]


@pytest.fixture
def sample_config_id(client: "TestClient") -> str:
    """Create and return a sample config ID.

    Args:
        client: TestClient fixture

    Returns:
        ID of the created config
    """
    config_data = {
        "name": "Test GPT-4 Config",
        "provider": "openai",
        "model_id": "gpt-4-turbo-preview",
        "temperature": 0.7,
        "max_tokens": 4096,
        "reasoning_effort": "medium",
        "extra_params": {"top_p": 0.95},
    }

    response = client.post("/api/configs", json=config_data)
    assert response.status_code == 201, f"Failed to create config: {response.text}"
    return response.json()["id"]


@pytest.fixture
def sample_config_anthropic(client: "TestClient") -> str:
    """Create a sample Anthropic config.

    Args:
        client: TestClient fixture

    Returns:
        ID of the created config
    """
    config_data = {
        "name": "Test Claude Config",
        "provider": "anthropic",
        "model_id": "claude-3-opus-20240229",
        "temperature": 0.1,
        "max_tokens": 8192,
    }

    response = client.post("/api/configs", json=config_data)
    assert response.status_code == 201
    return response.json()["id"]


@pytest.fixture
def sample_run_id(
    client: "TestClient", sample_prompt_id: str, sample_config_id: str
) -> str:
    """Create and return a sample run ID.

    Args:
        client: TestClient fixture
        sample_prompt_id: ID of prompt to use
        sample_config_id: ID of config to use

    Returns:
        ID of the created run
    """
    run_data = {
        "prompt_id": sample_prompt_id,
        "config_id": sample_config_id,
        "document_name": "contract_001.pdf",
    }

    # Mock background tasks to avoid actual execution
    with patch("mvp.api.runs.execute_run"):
        response = client.post("/api/runs", json=run_data)

    assert response.status_code == 202, f"Failed to create run: {response.text}"
    return response.json()["run_id"]


@pytest.fixture
def sample_completed_run(
    client: "TestClient",
    sample_prompt_id: str,
    sample_config_id: str,
    test_data_dir: Path,
) -> str:
    """Create a sample completed run with metrics and output.

    Args:
        client: TestClient fixture
        sample_prompt_id: ID of prompt to use
        sample_config_id: ID of config to use
        test_data_dir: Temporary data directory

    Returns:
        ID of the created run
    """
    run_data = {
        "prompt_id": sample_prompt_id,
        "config_id": sample_config_id,
        "document_name": "contract_001.pdf",
    }

    # Mock background tasks to avoid actual execution
    with patch("mvp.api.runs.execute_run"):
        response = client.post("/api/runs", json=run_data)

    assert response.status_code == 202
    run_id = response.json()["run_id"]

    # Manually update the run to completed status with metrics
    run_file = test_data_dir / "runs" / f"{run_id}.json"
    with open(run_file, "r") as f:
        run_data = json.load(f)
    run_data.update(
        {
            "status": "completed",
            "completed_at": datetime.utcnow().isoformat() + "Z",
            "output": {
                "contract_number": "CNT-2024-001",
                "start_date": "2024-01-01",
                "end_date": "2024-12-31",
                "party_name": "Test Corp",
            },
            "metrics": {
                "recall": 0.95,
                "precision": 0.92,
                "f1": 0.935,
                "latency_ms": 5234,
            },
            "cost_usd": 0.045,
            "tokens": {"input": 2048, "output": 512},
        }
    )
    with open(run_file, "w") as f:
        json.dump(run_data, f, indent=2)

    # Update the index as well
    index_file = test_data_dir / "runs" / "index.json"
    with open(index_file, "r") as f:
        index = json.load(f)
    for item in index.get("items", []):
        if item.get("id") == run_id:
            item["status"] = "completed"
            break
    with open(index_file, "w") as f:
        json.dump(index, f, indent=2)

    return run_id


# =============================================================================
# Mock Fixtures
# =============================================================================


@pytest.fixture
def mock_executor() -> Generator[MagicMock, None, None]:
    """Mock the execute_run function.

    Yields:
        MagicMock instance for the execute_run function
    """
    with patch("mvp.api.runs.execute_run") as mock:
        yield mock


@pytest.fixture
def mock_storage_error() -> Generator[MagicMock, None, None]:
    """Mock storage operations to simulate errors.

    Yields:
        MagicMock instance configured to raise exceptions
    """
    with patch("mvp.api.prompts._save_prompt") as mock_save:
        mock_save.side_effect = Exception("Storage error")
        yield mock_save


# =============================================================================
# Helper Functions
# =============================================================================


def create_test_prompt(client: "TestClient", **overrides) -> Dict[str, Any]:
    """Helper to create a test prompt with optional overrides.

    Args:
        client: TestClient instance
        **overrides: Fields to override in default prompt data

    Returns:
        Created prompt data from response
    """
    prompt_data = {
        "name": overrides.get("name", "Test Prompt"),
        "description": overrides.get("description", "Test description"),
        "blocks": overrides.get(
            "blocks", [{"title": "Block 1", "body": "Test body", "comment": None}]
        ),
        "tags": overrides.get("tags", ["test"]),
    }

    response = client.post("/api/prompts", json=prompt_data)
    assert response.status_code == 201
    return response.json()


def create_test_config(client: "TestClient", **overrides) -> Dict[str, Any]:
    """Helper to create a test config with optional overrides.

    Args:
        client: TestClient instance
        **overrides: Fields to override in default config data

    Returns:
        Created config data from response
    """
    config_data = {
        "name": overrides.get("name", "Test Config"),
        "provider": overrides.get("provider", "openai"),
        "model_id": overrides.get("model_id", "gpt-4"),
        "temperature": overrides.get("temperature", 0.7),
        "max_tokens": overrides.get("max_tokens", 1000),
        "extra_params": overrides.get("extra_params", {}),
    }

    if "reasoning_effort" in overrides:
        config_data["reasoning_effort"] = overrides["reasoning_effort"]

    response = client.post("/api/configs", json=config_data)
    assert response.status_code == 201
    return response.json()
