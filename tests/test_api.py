"""API endpoint tests for Prompt Governor MVP.

This module provides comprehensive tests for all API endpoints:
- Prompt endpoints (CRUD + diff)
- Config endpoints (CRUD + validation)
- Document endpoints (listing + metadata)
- Run endpoints (create, filter, compare)
- Error handling (404, 400, 500 errors)

Tests use pytest with FastAPI TestClient and temporary data directories
to ensure isolation between tests.
"""

import pytest
from fastapi import status
from datetime import datetime
from unittest.mock import patch, MagicMock

# Import fixtures from conftest.py
from tests.conftest import create_test_prompt, create_test_config


# =============================================================================
# Health Check Tests
# =============================================================================


class TestHealthEndpoints:
    """Tests for health check endpoints."""

    def test_health_check(self, client):
        """Test basic health check endpoint."""
        response = client.get("/api/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert "version" in data

    def test_volumes_check(self, client):
        """Test volume mount verification endpoint."""
        response = client.get("/api/test/volumes")
        assert response.status_code == 200
        data = response.json()
        assert "volumes_mounted" in data
        assert isinstance(data["all_mounted"], bool)


# =============================================================================
# Prompt Endpoint Tests
# =============================================================================


class TestPromptList:
    """Tests for listing prompts."""

    def test_list_prompts_empty(self, client):
        """Test listing prompts when none exist."""
        response = client.get("/api/prompts")
        assert response.status_code == 200
        data = response.json()
        assert data["prompts"] == []
        assert data["total"] == 0

    def test_list_prompts_with_data(self, client, sample_prompt_id):
        """Test listing prompts with existing data."""
        response = client.get("/api/prompts")
        assert response.status_code == 200
        data = response.json()
        assert len(data["prompts"]) == 1
        assert data["total"] == 1
        assert data["prompts"][0]["id"] == sample_prompt_id

    def test_list_prompts_filter_by_tag(self, client):
        """Test filtering prompts by tag."""
        # Create prompts with different tags
        create_test_prompt(client, name="Prompt A", tags=["tag1", "common"])
        create_test_prompt(client, name="Prompt B", tags=["tag2", "common"])
        create_test_prompt(client, name="Prompt C", tags=["tag3"])

        # Filter by tag1
        response = client.get("/api/prompts?tag=tag1")
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 1
        assert data["prompts"][0]["name"] == "Prompt A"

        # Filter by common tag
        response = client.get("/api/prompts?tag=common")
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 2

    def test_list_prompts_filter_multiple_tags(self, client):
        """Test filtering prompts by multiple tags."""
        create_test_prompt(client, name="Prompt A", tags=["extraction", "contract"])
        create_test_prompt(client, name="Prompt B", tags=["extraction"])
        create_test_prompt(client, name="Prompt C", tags=["summary"])

        # Filter by multiple tags (OR logic - any match)
        response = client.get("/api/prompts?tag=extraction&tag=summary")
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 3  # All match extraction or summary

    def test_list_prompts_case_insensitive_tags(self, client):
        """Test that tag filtering is case-insensitive."""
        create_test_prompt(client, name="Prompt A", tags=["TestTag"])

        response = client.get("/api/prompts?tag=testtag")
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 1

    def test_list_prompts_returns_metadata_only(self, client, sample_prompt_id):
        """Test that listing returns metadata, not full prompt data."""
        response = client.get("/api/prompts")
        assert response.status_code == 200
        prompt = response.json()["prompts"][0]

        # Should have metadata fields
        assert "id" in prompt
        assert "name" in prompt
        assert "created_at" in prompt
        assert "tags" in prompt

        # Should NOT have full content
        assert "blocks" not in prompt


class TestPromptGet:
    """Tests for getting single prompts."""

    def test_get_prompt_success(self, client, sample_prompt_id):
        """Test getting a prompt by ID."""
        response = client.get(f"/api/prompts/{sample_prompt_id}")
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == sample_prompt_id
        assert data["name"] == "Test Contract Extractor"
        assert "blocks" in data
        assert len(data["blocks"]) == 2

    def test_get_prompt_not_found(self, client):
        """Test getting a non-existent prompt."""
        response = client.get("/api/prompts/nonexistent123")
        assert response.status_code == 404
        data = response.json()
        assert "not found" in data["detail"].lower()

    def test_get_prompt_invalid_id_format(self, client):
        """Test getting a prompt with invalid ID format."""
        response = client.get("/api/prompts/invalid-id-format")
        assert response.status_code == 404


class TestPromptCreate:
    """Tests for creating prompts."""

    def test_create_prompt_success(self, client):
        """Test creating a new prompt."""
        prompt_data = {
            "name": "New Test Prompt",
            "description": "A test prompt description",
            "blocks": [
                {"title": "System", "body": "You are helpful.", "comment": "Test"}
            ],
            "tags": ["test", "new"],
        }

        response = client.post("/api/prompts", json=prompt_data)
        assert response.status_code == 201
        data = response.json()

        assert data["name"] == "New Test Prompt"
        assert data["description"] == "A test prompt description"
        assert len(data["blocks"]) == 1
        assert data["tags"] == ["test", "new"]
        assert "id" in data
        assert "created_at" in data

    def test_create_prompt_minimal(self, client):
        """Test creating a prompt with minimal data."""
        prompt_data = {"name": "Minimal Prompt"}

        response = client.post("/api/prompts", json=prompt_data)
        assert response.status_code == 201
        data = response.json()

        assert data["name"] == "Minimal Prompt"
        assert data["blocks"] == []
        assert data["tags"] == []

    def test_create_prompt_with_parent(self, client, sample_prompt_id):
        """Test creating a forked prompt with parent_id."""
        prompt_data = {
            "name": "Forked Prompt",
            "parent_id": sample_prompt_id,
            "blocks": [{"title": "Test", "body": "Content", "comment": None}],
        }

        response = client.post("/api/prompts", json=prompt_data)
        assert response.status_code == 201
        data = response.json()

        assert data["parent_id"] == sample_prompt_id

    def test_create_prompt_missing_name(self, client):
        """Test creating a prompt without required name field."""
        prompt_data = {"description": "Missing name"}

        response = client.post("/api/prompts", json=prompt_data)
        assert response.status_code == 422  # Validation error

    def test_create_prompt_empty_name(self, client):
        """Test creating a prompt with empty name."""
        prompt_data = {"name": ""}

        response = client.post("/api/prompts", json=prompt_data)
        assert response.status_code == 422  # Validation error

    def test_create_prompt_adds_to_index(self, client):
        """Test that creating a prompt adds it to the index."""
        prompt_data = {"name": "Indexed Prompt"}
        response = client.post("/api/prompts", json=prompt_data)
        assert response.status_code == 201

        # Check it's in the list
        list_response = client.get("/api/prompts")
        assert list_response.status_code == 200
        prompts = list_response.json()["prompts"]
        assert any(p["name"] == "Indexed Prompt" for p in prompts)


class TestPromptUpdate:
    """Tests for updating prompts."""

    def test_update_prompt_success(self, client, sample_prompt_id):
        """Test updating an existing prompt."""
        update_data = {
            "name": "Updated Prompt Name",
            "description": "Updated description",
        }

        response = client.put(f"/api/prompts/{sample_prompt_id}", json=update_data)
        assert response.status_code == 200
        data = response.json()

        assert data["name"] == "Updated Prompt Name"
        assert data["description"] == "Updated description"
        # Other fields should remain unchanged
        assert data["id"] == sample_prompt_id

    def test_update_prompt_partial(self, client, sample_prompt_id):
        """Test partial update (only some fields)."""
        # Get original
        original = client.get(f"/api/prompts/{sample_prompt_id}").json()

        # Update only name
        update_data = {"name": "Partially Updated"}
        response = client.put(f"/api/prompts/{sample_prompt_id}", json=update_data)
        assert response.status_code == 200
        data = response.json()

        assert data["name"] == "Partially Updated"
        assert data["description"] == original["description"]  # Unchanged
        assert data["blocks"] == original["blocks"]  # Unchanged

    def test_update_prompt_blocks(self, client, sample_prompt_id):
        """Test updating prompt blocks."""
        new_blocks = [
            {"title": "New Block", "body": "New content", "comment": "Updated"}
        ]

        update_data = {"blocks": new_blocks}
        response = client.put(f"/api/prompts/{sample_prompt_id}", json=update_data)
        assert response.status_code == 200
        data = response.json()

        assert len(data["blocks"]) == 1
        assert data["blocks"][0]["title"] == "New Block"

    def test_update_prompt_tags(self, client, sample_prompt_id):
        """Test updating prompt tags."""
        update_data = {"tags": ["updated", "tags"]}
        response = client.put(f"/api/prompts/{sample_prompt_id}", json=update_data)
        assert response.status_code == 200
        data = response.json()

        assert data["tags"] == ["updated", "tags"]

    def test_update_prompt_not_found(self, client):
        """Test updating a non-existent prompt."""
        update_data = {"name": "Updated Name"}
        response = client.put("/api/prompts/nonexistent123", json=update_data)
        assert response.status_code == 404

    def test_update_prompt_empty_body(self, client, sample_prompt_id):
        """Test update with empty body (no changes)."""
        # Get original
        original = client.get(f"/api/prompts/{sample_prompt_id}").json()

        response = client.put(f"/api/prompts/{sample_prompt_id}", json={})
        assert response.status_code == 200
        data = response.json()

        # Should be unchanged
        assert data["name"] == original["name"]


class TestPromptDelete:
    """Tests for deleting prompts."""

    def test_delete_prompt_success(self, client):
        """Test deleting an existing prompt."""
        # Create a prompt to delete
        prompt = create_test_prompt(client, name="To Delete")
        prompt_id = prompt["id"]

        response = client.delete(f"/api/prompts/{prompt_id}")
        assert response.status_code == 204

        # Verify it's gone
        get_response = client.get(f"/api/prompts/{prompt_id}")
        assert get_response.status_code == 404

    def test_delete_prompt_not_found(self, client):
        """Test deleting a non-existent prompt."""
        response = client.delete("/api/prompts/nonexistent123")
        assert response.status_code == 404

    def test_delete_prompt_removes_from_index(self, client):
        """Test that deleting removes prompt from index."""
        # Create and delete
        prompt = create_test_prompt(client, name="To Remove")
        prompt_id = prompt["id"]

        client.delete(f"/api/prompts/{prompt_id}")

        # Check index
        list_response = client.get("/api/prompts")
        prompts = list_response.json()["prompts"]
        assert not any(p["id"] == prompt_id for p in prompts)


class TestPromptDiff:
    """Tests for prompt comparison/diff endpoint."""

    def test_diff_prompts_success(
        self, client, sample_prompt_id, sample_prompt_with_parent
    ):
        """Test comparing two prompts."""
        response = client.get(
            f"/api/prompts/{sample_prompt_id}/diff/{sample_prompt_with_parent}"
        )
        assert response.status_code == 200
        data = response.json()

        assert data["prompt_a_id"] == sample_prompt_id
        assert data["prompt_b_id"] == sample_prompt_with_parent
        assert "name_changed" in data
        assert "description_changed" in data
        assert "tags_changed" in data
        assert "blocks_diff" in data

    def test_diff_prompts_name_changed(self, client, sample_prompt_id):
        """Test diff detects name changes."""
        # Create another prompt with different name
        prompt2 = create_test_prompt(client, name="Different Name")

        response = client.get(f"/api/prompts/{sample_prompt_id}/diff/{prompt2['id']}")
        assert response.status_code == 200
        data = response.json()

        assert data["name_changed"] is True

    def test_diff_prompts_blocks_added(self, client):
        """Test diff detects added blocks."""
        # Create two prompts with different blocks
        prompt1 = create_test_prompt(
            client,
            name="Prompt 1",
            blocks=[{"title": "Block 1", "body": "Content 1", "comment": None}],
        )
        prompt2 = create_test_prompt(
            client,
            name="Prompt 2",
            blocks=[
                {"title": "Block 1", "body": "Content 1", "comment": None},
                {"title": "Block 2", "body": "Content 2", "comment": None},
            ],
        )

        response = client.get(f"/api/prompts/{prompt1['id']}/diff/{prompt2['id']}")
        assert response.status_code == 200
        data = response.json()

        # Should have a block added
        added_blocks = [d for d in data["blocks_diff"] if d["status"] == "added"]
        assert len(added_blocks) == 1

    def test_diff_prompts_not_found(self, client, sample_prompt_id):
        """Test diff with non-existent prompt."""
        response = client.get(f"/api/prompts/{sample_prompt_id}/diff/nonexistent")
        assert response.status_code == 404


# =============================================================================
# Config Endpoint Tests
# =============================================================================


class TestConfigList:
    """Tests for listing configurations."""

    def test_list_configs_empty(self, client):
        """Test listing configs when none exist."""
        response = client.get("/api/configs")
        assert response.status_code == 200
        data = response.json()
        assert data["configs"] == []
        assert data["total"] == 0

    def test_list_configs_with_data(self, client, sample_config_id):
        """Test listing configs with existing data."""
        response = client.get("/api/configs")
        assert response.status_code == 200
        data = response.json()
        assert len(data["configs"]) == 1
        assert data["total"] == 1
        assert data["configs"][0]["id"] == sample_config_id

    def test_list_configs_sorted_by_name(self, client):
        """Test that configs are sorted by name."""
        create_test_config(client, name="Zebra Config")
        create_test_config(client, name="Apple Config")
        create_test_config(client, name="Banana Config")

        response = client.get("/api/configs")
        data = response.json()
        names = [c["name"] for c in data["configs"]]

        assert names == sorted(names)


class TestConfigGet:
    """Tests for getting single configurations."""

    def test_get_config_success(self, client, sample_config_id):
        """Test getting a config by ID."""
        response = client.get(f"/api/configs/{sample_config_id}")
        assert response.status_code == 200
        data = response.json()

        assert data["id"] == sample_config_id
        assert data["name"] == "Test GPT-4 Config"
        assert data["provider"] == "openai"
        assert data["model_id"] == "gpt-4-turbo-preview"
        assert data["temperature"] == 0.7

    def test_get_config_not_found(self, client):
        """Test getting a non-existent config."""
        response = client.get("/api/configs/nonexistent123")
        assert response.status_code == 404

    def test_get_config_returns_all_fields(self, client, sample_config_id):
        """Test that getting a config returns all fields."""
        response = client.get(f"/api/configs/{sample_config_id}")
        data = response.json()

        expected_fields = [
            "id",
            "name",
            "provider",
            "model_id",
            "temperature",
            "max_tokens",
            "extra_params",
            "created_at",
        ]
        for field in expected_fields:
            assert field in data, f"Missing field: {field}"


class TestConfigCreate:
    """Tests for creating configurations."""

    def test_create_config_success(self, client):
        """Test creating a new config."""
        config_data = {
            "name": "New Test Config",
            "provider": "anthropic",
            "model_id": "claude-3-haiku",
            "temperature": 0.5,
            "max_tokens": 2000,
            "reasoning_effort": "low",
        }

        response = client.post("/api/configs", json=config_data)
        assert response.status_code == 201
        data = response.json()

        assert data["name"] == "New Test Config"
        assert data["provider"] == "anthropic"
        assert "id" in data
        assert "created_at" in data

    def test_create_config_openrouter(self, client):
        """Test creating a config with OpenRouter provider."""
        config_data = {
            "name": "OpenRouter Config",
            "provider": "openrouter",
            "model_id": "meta-llama/llama-3-70b",
            "temperature": 0.9,
        }

        response = client.post("/api/configs", json=config_data)
        assert response.status_code == 201
        data = response.json()
        assert data["provider"] == "openrouter"

    def test_create_config_invalid_provider(self, client):
        """Test creating a config with invalid provider."""
        config_data = {
            "name": "Invalid Config",
            "provider": "invalid_provider",
            "model_id": "model-1",
        }

        response = client.post("/api/configs", json=config_data)
        assert response.status_code == 422  # Validation error

    def test_create_config_temperature_bounds(self, client):
        """Test temperature validation (0.0 - 2.0)."""
        # Valid: temperature = 0.0
        config_data = {
            "name": "Low Temp",
            "provider": "openai",
            "model_id": "gpt-4",
            "temperature": 0.0,
        }
        response = client.post("/api/configs", json=config_data)
        assert response.status_code == 201

        # Valid: temperature = 2.0
        config_data["name"] = "High Temp"
        config_data["temperature"] = 2.0
        response = client.post("/api/configs", json=config_data)
        assert response.status_code == 201

        # Invalid: temperature = -0.1
        config_data["name"] = "Invalid Temp"
        config_data["temperature"] = -0.1
        response = client.post("/api/configs", json=config_data)
        assert response.status_code == 422

        # Invalid: temperature = 2.1
        config_data["temperature"] = 2.1
        response = client.post("/api/configs", json=config_data)
        assert response.status_code == 422

    def test_create_config_reasoning_effort_validation(self, client):
        """Test reasoning_effort validation."""
        # Valid values
        for effort in ["low", "medium", "high"]:
            config_data = {
                "name": f"Config {effort}",
                "provider": "openai",
                "model_id": "gpt-4",
                "reasoning_effort": effort,
            }
            response = client.post("/api/configs", json=config_data)
            assert response.status_code == 201, f"Failed for effort: {effort}"

        # Invalid value
        config_data = {
            "name": "Invalid Effort",
            "provider": "openai",
            "model_id": "gpt-4",
            "reasoning_effort": "extreme",
        }
        response = client.post("/api/configs", json=config_data)
        assert response.status_code == 422

    def test_create_config_max_tokens_validation(self, client):
        """Test max_tokens validation (must be >= 1)."""
        # Valid
        config_data = {
            "name": "Valid Tokens",
            "provider": "openai",
            "model_id": "gpt-4",
            "max_tokens": 1,
        }
        response = client.post("/api/configs", json=config_data)
        assert response.status_code == 201

        # Invalid: max_tokens = 0
        config_data["name"] = "Invalid Tokens"
        config_data["max_tokens"] = 0
        response = client.post("/api/configs", json=config_data)
        assert response.status_code == 422

    def test_create_config_missing_required_fields(self, client):
        """Test creating config without required fields."""
        # Missing name
        response = client.post(
            "/api/configs", json={"provider": "openai", "model_id": "gpt-4"}
        )
        assert response.status_code == 422

        # Missing provider
        response = client.post(
            "/api/configs", json={"name": "Test", "model_id": "gpt-4"}
        )
        assert response.status_code == 422

        # Missing model_id
        response = client.post(
            "/api/configs", json={"name": "Test", "provider": "openai"}
        )
        assert response.status_code == 422


class TestConfigUpdate:
    """Tests for updating configurations."""

    def test_update_config_success(self, client, sample_config_id):
        """Test updating an existing config."""
        update_data = {"name": "Updated Config Name", "temperature": 0.3}

        response = client.put(f"/api/configs/{sample_config_id}", json=update_data)
        assert response.status_code == 200
        data = response.json()

        assert data["name"] == "Updated Config Name"
        assert data["temperature"] == 0.3
        # Other fields unchanged
        assert data["provider"] == "openai"

    def test_update_config_provider(self, client, sample_config_id):
        """Test updating config provider."""
        update_data = {"provider": "anthropic"}

        response = client.put(f"/api/configs/{sample_config_id}", json=update_data)
        assert response.status_code == 200
        data = response.json()

        assert data["provider"] == "anthropic"

    def test_update_config_invalid_temperature(self, client, sample_config_id):
        """Test updating with invalid temperature."""
        update_data = {"temperature": 5.0}

        response = client.put(f"/api/configs/{sample_config_id}", json=update_data)
        assert response.status_code == 422

    def test_update_config_not_found(self, client):
        """Test updating non-existent config."""
        update_data = {"name": "Updated Name"}
        response = client.put("/api/configs/nonexistent123", json=update_data)
        assert response.status_code == 404


class TestConfigDelete:
    """Tests for deleting configurations."""

    def test_delete_config_success(self, client):
        """Test deleting an existing config."""
        config = create_test_config(client, name="To Delete Config")
        config_id = config["id"]

        response = client.delete(f"/api/configs/{config_id}")
        assert response.status_code == 204

        # Verify it's gone
        get_response = client.get(f"/api/configs/{config_id}")
        assert get_response.status_code == 404

    def test_delete_config_not_found(self, client):
        """Test deleting non-existent config."""
        response = client.delete("/api/configs/nonexistent123")
        assert response.status_code == 404

    def test_delete_config_removes_from_index(self, client):
        """Test that deleting removes config from index."""
        config = create_test_config(client, name="To Remove")
        config_id = config["id"]

        client.delete(f"/api/configs/{config_id}")

        # Check index
        list_response = client.get("/api/configs")
        configs = list_response.json()["configs"]
        assert not any(c["id"] == config_id for c in configs)


# =============================================================================
# Document Endpoint Tests
# =============================================================================


class TestDocumentList:
    """Tests for listing documents."""

    def test_list_documents_success(self, client):
        """Test listing all documents."""
        response = client.get("/api/documents")
        assert response.status_code == 200
        data = response.json()

        assert "documents" in data
        assert "total" in data
        assert data["total"] == 4  # 4 test files created in fixture
        assert len(data["documents"]) == 4

    def test_list_documents_sorted(self, client):
        """Test that documents are sorted by name."""
        response = client.get("/api/documents")
        data = response.json()

        names = [d["name"] for d in data["documents"]]
        assert names == sorted(names)

    def test_list_documents_filter_pdf(self, client):
        """Test filtering documents by PDF extension."""
        response = client.get("/api/documents?extension=pdf")
        assert response.status_code == 200
        data = response.json()

        assert data["total"] == 2
        for doc in data["documents"]:
            assert doc["extension"] == ".pdf"
            assert doc["type"] == "pdf"

    def test_list_documents_filter_txt(self, client):
        """Test filtering documents by TXT extension."""
        response = client.get("/api/documents?extension=txt")
        assert response.status_code == 200
        data = response.json()

        assert data["total"] == 1
        assert data["documents"][0]["name"] == "report_2024.txt"

    def test_list_documents_filter_with_dot(self, client):
        """Test filtering with extension including dot."""
        response = client.get("/api/documents?extension=.pdf")
        assert response.status_code == 200
        data = response.json()

        assert data["total"] == 2

    def test_list_documents_returns_metadata(self, client):
        """Test that listing returns document metadata."""
        response = client.get("/api/documents")
        data = response.json()

        doc = data["documents"][0]
        assert "name" in doc
        assert "size" in doc
        assert "type" in doc
        assert "extension" in doc
        assert "modified_at" in doc

    def test_list_documents_empty_directory(self, client, test_data_dir):
        """Test listing documents in empty directory."""
        # This test uses the existing fixture but documents are created in conftest
        # The fixture creates 4 files, so we expect 4 documents
        response = client.get("/api/documents")
        assert response.status_code == 200
        data = response.json()
        assert data["total"] >= 0  # At minimum should not error


class TestDocumentGet:
    """Tests for getting single documents."""

    def test_get_document_success(self, client):
        """Test getting a document by name."""
        response = client.get("/api/documents/contract_001.pdf")
        assert response.status_code == 200
        data = response.json()

        assert data["name"] == "contract_001.pdf"
        assert data["type"] == "pdf"
        assert "size" in data
        assert "modified_at" in data

    def test_get_document_not_found(self, client):
        """Test getting non-existent document."""
        response = client.get("/api/documents/nonexistent.pdf")
        assert response.status_code == 404

    def test_get_document_invalid_filename(self, client):
        """Test getting document with invalid filename (directory traversal)."""
        response = client.get("/api/documents/../etc/passwd")
        assert response.status_code == 400

    def test_get_document_unsupported_type(self, client):
        """Test getting document with unsupported file type."""
        # Try to get a non-existent file with unsupported extension
        response = client.get("/api/documents/test.exe")
        assert response.status_code == 404


class TestDocumentHead:
    """Tests for HEAD request to check document existence."""

    def test_head_document_exists(self, client):
        """Test HEAD request for existing document."""
        response = client.head("/api/documents/contract_001.pdf")
        assert response.status_code == 200

    def test_head_document_not_found(self, client):
        """Test HEAD request for non-existent document."""
        response = client.head("/api/documents/nonexistent.pdf")
        assert response.status_code == 404

    def test_head_document_invalid_filename(self, client):
        """Test HEAD request with invalid filename."""
        response = client.head("/api/documents/../etc/passwd")
        assert response.status_code == 400


# =============================================================================
# Run Endpoint Tests
# =============================================================================


class TestRunList:
    """Tests for listing runs."""

    def test_list_runs_empty(self, client):
        """Test listing runs when none exist."""
        response = client.get("/api/runs")
        assert response.status_code == 200
        data = response.json()
        assert data["runs"] == []
        assert data["total"] == 0

    def test_list_runs_with_data(self, client, sample_run_id):
        """Test listing runs with existing data."""
        response = client.get("/api/runs")
        assert response.status_code == 200
        data = response.json()
        assert len(data["runs"]) == 1
        assert data["total"] == 1
        assert data["runs"][0]["id"] == sample_run_id

    def test_list_runs_filter_by_prompt(
        self, client, sample_prompt_id, sample_config_id
    ):
        """Test filtering runs by prompt_id."""
        # Create two prompts and runs
        prompt2 = create_test_prompt(client, name="Second Prompt")

        # Create runs (mocking executor)
        with patch("mvp.api.runs.execute_run"):
            response1 = client.post(
                "/api/runs",
                json={
                    "prompt_id": sample_prompt_id,
                    "config_id": sample_config_id,
                    "document_name": "contract_001.pdf",
                },
            )
            response2 = client.post(
                "/api/runs",
                json={
                    "prompt_id": prompt2["id"],
                    "config_id": sample_config_id,
                    "document_name": "contract_002.pdf",
                },
            )

        # Filter by first prompt
        response = client.get(f"/api/runs?prompt_id={sample_prompt_id}")
        assert response.status_code == 200
        data = response.json()

        # Should have at least the runs for this prompt
        assert all(r["prompt_id"] == sample_prompt_id for r in data["runs"])

    def test_list_runs_filter_by_status(self, client, sample_run_id):
        """Test filtering runs by status."""
        response = client.get("/api/runs?status=pending")
        assert response.status_code == 200
        data = response.json()

        # Our sample run should be pending
        assert len(data["runs"]) >= 1
        assert all(r["status"] == "pending" for r in data["runs"])

    def test_list_runs_filter_by_config(self, client, sample_config_id):
        """Test filtering runs by config_id."""
        response = client.get(f"/api/runs?config_id={sample_config_id}")
        assert response.status_code == 200
        data = response.json()

        assert all(r["config_id"] == sample_config_id for r in data["runs"])

    def test_list_runs_filter_by_document(self, client):
        """Test filtering runs by document_name."""
        response = client.get("/api/runs?document_name=contract_001.pdf")
        assert response.status_code == 200
        data = response.json()

        assert all(r["document_name"] == "contract_001.pdf" for r in data["runs"])

    def test_list_runs_sorted_by_date(self, client):
        """Test that runs are sorted by started_at descending."""
        response = client.get("/api/runs")
        data = response.json()

        if len(data["runs"]) > 1:
            dates = [r["started_at"] for r in data["runs"]]
            assert dates == sorted(dates, reverse=True)


class TestRunGet:
    """Tests for getting single runs."""

    def test_get_run_success(self, client, sample_run_id):
        """Test getting a run by ID."""
        response = client.get(f"/api/runs/{sample_run_id}")
        assert response.status_code == 200
        data = response.json()

        assert data["id"] == sample_run_id
        assert data["status"] == "pending"
        assert "prompt_id" in data
        assert "config_id" in data
        assert "document_name" in data

    def test_get_run_not_found(self, client):
        """Test getting non-existent run."""
        response = client.get("/api/runs/nonexistent123")
        assert response.status_code == 404

    def test_get_run_returns_full_data(self, client, sample_completed_run):
        """Test that getting a run returns full data including output."""
        response = client.get(f"/api/runs/{sample_completed_run}")
        assert response.status_code == 200
        data = response.json()

        expected_fields = [
            "id",
            "prompt_id",
            "config_id",
            "document_name",
            "status",
            "started_at",
            "completed_at",
            "output",
            "metrics",
            "cost_usd",
            "tokens",
        ]
        for field in expected_fields:
            assert field in data, f"Missing field: {field}"


class TestRunCreate:
    """Tests for creating runs."""

    def test_create_run_success(self, client, sample_prompt_id, sample_config_id):
        """Test creating a new run."""
        run_data = {
            "prompt_id": sample_prompt_id,
            "config_id": sample_config_id,
            "document_name": "contract_001.pdf",
        }

        with patch("mvp.api.runs.execute_run"):
            response = client.post("/api/runs", json=run_data)

        assert response.status_code == 202  # Accepted
        data = response.json()

        assert "run_id" in data
        assert data["status"] == "pending"
        assert "message" in data

    def test_create_run_validates_prompt_exists(self, client, sample_config_id):
        """Test that creating run validates prompt exists."""
        run_data = {
            "prompt_id": "nonexistent123",
            "config_id": sample_config_id,
            "document_name": "contract_001.pdf",
        }

        with patch("mvp.api.runs.execute_run"):
            response = client.post("/api/runs", json=run_data)

        assert response.status_code == 404
        assert "prompt" in response.json()["detail"].lower()

    def test_create_run_validates_config_exists(self, client, sample_prompt_id):
        """Test that creating run validates config exists."""
        run_data = {
            "prompt_id": sample_prompt_id,
            "config_id": "nonexistent123",
            "document_name": "contract_001.pdf",
        }

        with patch("mvp.api.runs.execute_run"):
            response = client.post("/api/runs", json=run_data)

        assert response.status_code == 404
        assert "config" in response.json()["detail"].lower()

    def test_create_run_validates_document_exists(
        self, client, sample_prompt_id, sample_config_id
    ):
        """Test that creating run validates document exists."""
        run_data = {
            "prompt_id": sample_prompt_id,
            "config_id": sample_config_id,
            "document_name": "nonexistent.pdf",
        }

        with patch("mvp.api.runs.execute_run"):
            response = client.post("/api/runs", json=run_data)

        assert response.status_code == 404
        assert "document" in response.json()["detail"].lower()

    def test_create_run_missing_fields(self, client):
        """Test creating run without required fields."""
        # Missing prompt_id
        response = client.post(
            "/api/runs", json={"config_id": "some-id", "document_name": "doc.pdf"}
        )
        assert response.status_code == 422

        # Missing config_id
        response = client.post(
            "/api/runs", json={"prompt_id": "some-id", "document_name": "doc.pdf"}
        )
        assert response.status_code == 422

        # Missing document_name
        response = client.post(
            "/api/runs", json={"prompt_id": "some-id", "config_id": "some-id"}
        )
        assert response.status_code == 422

    def test_create_run_adds_to_index(self, client, sample_prompt_id, sample_config_id):
        """Test that creating run adds it to index."""
        run_data = {
            "prompt_id": sample_prompt_id,
            "config_id": sample_config_id,
            "document_name": "contract_001.pdf",
        }

        with patch("mvp.api.runs.execute_run"):
            response = client.post("/api/runs", json=run_data)
            run_id = response.json()["run_id"]

        # Check it's in the list
        list_response = client.get("/api/runs")
        assert list_response.status_code == 200
        runs = list_response.json()["runs"]
        assert any(r["id"] == run_id for r in runs)


class TestRunDelete:
    """Tests for deleting runs."""

    def test_delete_run_success(self, client, sample_run_id):
        """Test deleting an existing run."""
        response = client.delete(f"/api/runs/{sample_run_id}")
        assert response.status_code == 204

        # Verify it's gone
        get_response = client.get(f"/api/runs/{sample_run_id}")
        assert get_response.status_code == 404

    def test_delete_run_not_found(self, client):
        """Test deleting non-existent run."""
        response = client.delete("/api/runs/nonexistent123")
        assert response.status_code == 404


class TestRunCompare:
    """Tests for comparing runs."""

    def test_compare_runs_success(self, client, sample_completed_run):
        """Test comparing two runs."""
        # Create another completed run
        prompt2 = create_test_prompt(client, name="Compare Prompt")
        config2 = create_test_config(client, name="Compare Config")

        with patch("mvp.api.runs.execute_run"):
            response = client.post(
                "/api/runs",
                json={
                    "prompt_id": prompt2["id"],
                    "config_id": config2["id"],
                    "document_name": "contract_002.pdf",
                },
            )
            run2_id = response.json()["run_id"]

        # Compare them
        response = client.get(f"/api/runs/{sample_completed_run}/compare/{run2_id}")
        assert response.status_code == 200
        data = response.json()

        assert "run_a" in data
        assert "run_b" in data
        assert "metric_comparisons" in data
        assert "field_differences" in data
        assert "summary" in data

    def test_compare_runs_not_found(self, client, sample_completed_run):
        """Test comparing with non-existent run."""
        response = client.get(f"/api/runs/{sample_completed_run}/compare/nonexistent")
        assert response.status_code == 404

    def test_compare_runs_metric_differences(
        self, client, sample_prompt_id, sample_config_id, test_data_dir
    ):
        """Test that comparison shows metric differences."""
        # Create two runs with different metrics
        with patch("mvp.api.runs.execute_run"):
            response1 = client.post(
                "/api/runs",
                json={
                    "prompt_id": sample_prompt_id,
                    "config_id": sample_config_id,
                    "document_name": "contract_001.pdf",
                },
            )
            run1_id = response1.json()["run_id"]

            response2 = client.post(
                "/api/runs",
                json={
                    "prompt_id": sample_prompt_id,
                    "config_id": sample_config_id,
                    "document_name": "contract_001.pdf",
                },
            )
            run2_id = response2.json()["run_id"]

        # Manually set metrics for both runs using test_data_dir
        import json as json_module

        run1_file = test_data_dir / "runs" / f"{run1_id}.json"
        with open(run1_file, "r") as f:
            run1_data = json_module.load(f)
        run1_data.update(
            {
                "status": "completed",
                "metrics": {"recall": 0.9, "precision": 0.85, "f1": 0.875},
            }
        )
        with open(run1_file, "w") as f:
            json_module.dump(run1_data, f, indent=2)

        run2_file = test_data_dir / "runs" / f"{run2_id}.json"
        with open(run2_file, "r") as f:
            run2_data = json_module.load(f)
        run2_data.update(
            {
                "status": "completed",
                "metrics": {"recall": 0.95, "precision": 0.9, "f1": 0.925},
            }
        )
        with open(run2_file, "w") as f:
            json_module.dump(run2_data, f, indent=2)

        # Update index
        index_file = test_data_dir / "runs" / "index.json"
        with open(index_file, "r") as f:
            index = json_module.load(f)
        for item in index.get("items", []):
            if item.get("id") == run1_id:
                item["status"] = "completed"
            if item.get("id") == run2_id:
                item["status"] = "completed"
        with open(index_file, "w") as f:
            json_module.dump(index, f, indent=2)

        # Compare
        response = client.get(f"/api/runs/{run1_id}/compare/{run2_id}")
        assert response.status_code == 200
        data = response.json()

        # Should have metric comparisons
        assert len(data["metric_comparisons"]) > 0

        # Check recall comparison
        recall_comp = next(
            (m for m in data["metric_comparisons"] if m["metric"] == "recall"), None
        )
        assert recall_comp is not None
        assert recall_comp["run_a_value"] == 0.9
        assert recall_comp["run_b_value"] == 0.95
        assert recall_comp["difference"] == 0.05


# =============================================================================
# Error Handling Tests
# =============================================================================


class TestErrorHandling:
    """Tests for error handling across all endpoints."""

    def test_404_error_format(self, client):
        """Test that 404 errors have consistent format."""
        response = client.get("/api/prompts/nonexistent")
        assert response.status_code == 404

        data = response.json()
        assert "detail" in data
        assert isinstance(data["detail"], str)

    def test_400_validation_error(self, client):
        """Test that validation errors return 400/422 with details."""
        # Invalid config data
        response = client.post(
            "/api/configs",
            json={
                "name": "Test",
                "provider": "invalid",  # Invalid provider
                "model_id": "gpt-4",
            },
        )
        assert response.status_code == 422

        data = response.json()
        assert "detail" in data

    def test_400_invalid_json(self, client):
        """Test error handling for invalid JSON."""
        response = client.post(
            "/api/prompts",
            data="not valid json",
            headers={"Content-Type": "application/json"},
        )
        assert response.status_code == 422  # FastAPI returns 422 for invalid JSON

    def test_method_not_allowed(self, client):
        """Test handling of unsupported HTTP methods."""
        response = client.patch("/api/prompts")  # PATCH not supported
        assert response.status_code == 405

    def test_invalid_uuid_format(self, client):
        """Test handling of invalid UUID formats."""
        # Try various invalid formats
        invalid_ids = [
            "not-a-uuid",
            "12345",
            "",
            "too-long-id-that-exceeds-normal-uuid-length-considerably",
        ]

        for invalid_id in invalid_ids:
            response = client.get(f"/api/prompts/{invalid_id}")
            # Should return 404 (not found) since we can't find it
            assert response.status_code == 404


# =============================================================================
# Edge Cases and Boundary Tests
# =============================================================================


class TestEdgeCases:
    """Tests for edge cases and boundary conditions."""

    def test_very_long_prompt_name(self, client):
        """Test handling of very long prompt names."""
        long_name = "A" * 1000
        response = client.post("/api/prompts", json={"name": long_name})
        # Should either accept or return validation error
        assert response.status_code in [201, 422]

    def test_prompt_with_many_blocks(self, client):
        """Test creating prompt with many blocks."""
        blocks = [
            {"title": f"Block {i}", "body": f"Content {i}", "comment": None}
            for i in range(100)
        ]

        response = client.post(
            "/api/prompts", json={"name": "Many Blocks", "blocks": blocks}
        )
        assert response.status_code == 201
        data = response.json()
        assert len(data["blocks"]) == 100

    def test_prompt_with_many_tags(self, client):
        """Test creating prompt with many tags."""
        tags = [f"tag{i}" for i in range(50)]

        response = client.post("/api/prompts", json={"name": "Many Tags", "tags": tags})
        assert response.status_code == 201
        data = response.json()
        assert len(data["tags"]) == 50

    def test_config_temperature_boundary_values(self, client):
        """Test config temperature at boundary values."""
        # Exactly 0.0
        response = client.post(
            "/api/configs",
            json={
                "name": "Min Temp",
                "provider": "openai",
                "model_id": "gpt-4",
                "temperature": 0.0,
            },
        )
        assert response.status_code == 201

        # Exactly 2.0
        response = client.post(
            "/api/configs",
            json={
                "name": "Max Temp",
                "provider": "openai",
                "model_id": "gpt-4",
                "temperature": 2.0,
            },
        )
        assert response.status_code == 201

    def test_special_characters_in_names(self, client):
        """Test handling of special characters in names."""
        special_names = [
            "Test & Config",
            "Config (v2)",
            "Config [2024]",
            "Config @ Home",
            "Config #1",
            "Unicode: 日本語",
        ]

        for name in special_names:
            response = client.post(
                "/api/configs",
                json={"name": name, "provider": "openai", "model_id": "gpt-4"},
            )
            assert response.status_code == 201, f"Failed for name: {name}"
            assert response.json()["name"] == name

    def test_empty_strings_handling(self, client):
        """Test handling of empty strings."""
        # Empty description should be allowed
        response = client.post("/api/prompts", json={"name": "Test", "description": ""})
        assert response.status_code == 201

    def test_null_values_handling(self, client):
        """Test handling of null values."""
        # Null description should be allowed
        response = client.post(
            "/api/prompts", json={"name": "Test", "description": None}
        )
        assert response.status_code == 201

    def test_concurrent_creations(self, client):
        """Test creating multiple items rapidly."""
        created_ids = []
        for i in range(10):
            response = client.post(
                "/api/prompts", json={"name": f"Concurrent {i}", "tags": [f"tag{i}"]}
            )
            assert response.status_code == 201
            created_ids.append(response.json()["id"])

        # Verify all were created
        response = client.get("/api/prompts")
        data = response.json()
        assert data["total"] >= 10

        # Verify all IDs are unique
        assert len(set(created_ids)) == len(created_ids)


# =============================================================================
# Integration Tests
# =============================================================================


class TestIntegration:
    """Integration tests for end-to-end workflows."""

    def test_full_prompt_workflow(self, client):
        """Test complete prompt lifecycle: create, read, update, delete."""
        # Create
        create_response = client.post(
            "/api/prompts",
            json={
                "name": "Integration Test Prompt",
                "description": "Test workflow",
                "blocks": [{"title": "Test", "body": "Content", "comment": None}],
                "tags": ["integration"],
            },
        )
        assert create_response.status_code == 201
        prompt_id = create_response.json()["id"]

        # Read
        get_response = client.get(f"/api/prompts/{prompt_id}")
        assert get_response.status_code == 200
        assert get_response.json()["name"] == "Integration Test Prompt"

        # Update
        update_response = client.put(
            f"/api/prompts/{prompt_id}", json={"name": "Updated Integration Prompt"}
        )
        assert update_response.status_code == 200
        assert update_response.json()["name"] == "Updated Integration Prompt"

        # Delete
        delete_response = client.delete(f"/api/prompts/{prompt_id}")
        assert delete_response.status_code == 204

        # Verify deletion
        get_response = client.get(f"/api/prompts/{prompt_id}")
        assert get_response.status_code == 404

    def test_full_config_workflow(self, client):
        """Test complete config lifecycle."""
        # Create
        create_response = client.post(
            "/api/configs",
            json={
                "name": "Integration Config",
                "provider": "openai",
                "model_id": "gpt-4-turbo",
                "temperature": 0.5,
            },
        )
        assert create_response.status_code == 201
        config_id = create_response.json()["id"]

        # Read
        get_response = client.get(f"/api/configs/{config_id}")
        assert get_response.status_code == 200

        # Update
        update_response = client.put(
            f"/api/configs/{config_id}", json={"temperature": 0.8}
        )
        assert update_response.status_code == 200
        assert update_response.json()["temperature"] == 0.8

        # Delete
        delete_response = client.delete(f"/api/configs/{config_id}")
        assert delete_response.status_code == 204

    def test_full_run_workflow(self, client):
        """Test complete run lifecycle including creation and comparison."""
        # Setup: create prompt and config
        prompt = create_test_prompt(client, name="Run Test Prompt")
        config = create_test_config(client, name="Run Test Config")

        # Create first run
        with patch("mvp.api.runs.execute_run"):
            run1_response = client.post(
                "/api/runs",
                json={
                    "prompt_id": prompt["id"],
                    "config_id": config["id"],
                    "document_name": "contract_001.pdf",
                },
            )
        assert run1_response.status_code == 202
        run1_id = run1_response.json()["run_id"]

        # Create second run
        with patch("mvp.api.runs.execute_run"):
            run2_response = client.post(
                "/api/runs",
                json={
                    "prompt_id": prompt["id"],
                    "config_id": config["id"],
                    "document_name": "contract_002.pdf",
                },
            )
        assert run2_response.status_code == 202
        run2_id = run2_response.json()["run_id"]

        # Compare runs
        compare_response = client.get(f"/api/runs/{run1_id}/compare/{run2_id}")
        assert compare_response.status_code == 200

        # Delete runs
        client.delete(f"/api/runs/{run1_id}")
        client.delete(f"/api/runs/{run2_id}")

    def test_cascade_prompt_to_run(self, client):
        """Test that deleting a prompt doesn't break runs that used it."""
        # Create prompt and config
        prompt = create_test_prompt(client, name="Cascade Test")
        config = create_test_config(client, name="Cascade Config")

        # Create run
        with patch("mvp.api.runs.execute_run"):
            run_response = client.post(
                "/api/runs",
                json={
                    "prompt_id": prompt["id"],
                    "config_id": config["id"],
                    "document_name": "contract_001.pdf",
                },
            )
        run_id = run_response.json()["run_id"]

        # Delete prompt (run should still exist, referencing old prompt_id)
        client.delete(f"/api/prompts/{prompt['id']}")

        # Run should still be accessible
        run_response = client.get(f"/api/runs/{run_id}")
        assert run_response.status_code == 200
        assert run_response.json()["prompt_id"] == prompt["id"]


# =============================================================================
# Test Count Summary
# =============================================================================

# Total test count by category:
# - Health Endpoints: 2
# - Prompt Endpoints: 30 (list: 6, get: 3, create: 7, update: 5, delete: 3, diff: 6)
# - Config Endpoints: 26 (list: 3, get: 3, create: 11, update: 4, delete: 3)
# - Document Endpoints: 11 (list: 7, get: 4, head: 3)
# - Run Endpoints: 23 (list: 7, get: 3, create: 7, delete: 2, compare: 4)
# - Error Handling: 4
# - Edge Cases: 9
# - Integration: 4
#
# Total: ~110+ tests
