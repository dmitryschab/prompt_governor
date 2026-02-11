"""Unit tests for the storage service.

Tests file-based JSON storage utilities including:
- JSON file I/O (sync and async)
- File listing operations
- UUID generation
- Collection index management
- Error handling for edge cases
"""

import json
import os
import tempfile
from pathlib import Path
from typing import Any, Dict
from unittest.mock import patch

import pytest

from mvp.services.storage import (
    COLLECTIONS,
    DATA_DIR,
    generate_id,
    list_files,
    list_files_async,
    load_index,
    load_index_async,
    load_json,
    load_json_async,
    save_index,
    save_index_async,
    save_json,
    save_json_async,
    get_collection_path,
    MAX_FILE_SIZE,
    MAX_INDEX_SIZE,
)


# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def temp_dir() -> Path:
    """Create a temporary directory for test files."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def sample_json_data() -> Dict[str, Any]:
    """Return sample JSON data for testing."""
    return {
        "name": "Test Data",
        "value": 42,
        "nested": {"key": "value", "list": [1, 2, 3]},
        "active": True,
        "null_field": None,
    }


# =============================================================================
# Test load_json
# =============================================================================


class TestLoadJson:
    """Tests for load_json function."""

    def test_load_valid_json_file(self, temp_dir: Path, sample_json_data: Dict) -> None:
        """Test loading a valid JSON file."""
        filepath = temp_dir / "test.json"
        with open(filepath, "w") as f:
            json.dump(sample_json_data, f)

        result = load_json(filepath)

        assert result == sample_json_data

    def test_load_json_with_string_path(self, temp_dir: Path) -> None:
        """Test loading JSON using string path."""
        filepath = temp_dir / "test.json"
        data = {"test": "data"}
        with open(filepath, "w") as f:
            json.dump(data, f)

        result = load_json(str(filepath))

        assert result == data

    def test_load_nonexistent_file_raises_error(self, temp_dir: Path) -> None:
        """Test that loading a non-existent file raises FileNotFoundError."""
        filepath = temp_dir / "nonexistent.json"

        with pytest.raises(FileNotFoundError) as exc_info:
            load_json(filepath)

        assert "not found" in str(exc_info.value).lower()
        assert "nonexistent" in str(exc_info.value)

    def test_load_invalid_json_raises_error(self, temp_dir: Path) -> None:
        """Test that loading invalid JSON raises JSONDecodeError."""
        filepath = temp_dir / "invalid.json"
        with open(filepath, "w") as f:
            f.write("not valid json{{")

        with pytest.raises(json.JSONDecodeError):
            load_json(filepath)

    def test_load_large_file_raises_error(self, temp_dir: Path) -> None:
        """Test that loading a file exceeding MAX_FILE_SIZE raises ValueError."""
        filepath = temp_dir / "large.json"
        # Create a file larger than MAX_FILE_SIZE (50MB)
        large_data = "x" * (MAX_FILE_SIZE + 1000)
        with open(filepath, "w") as f:
            f.write(f'"{large_data}"')

        with pytest.raises(ValueError) as exc_info:
            load_json(filepath)

        assert "exceeds" in str(exc_info.value).lower()
        assert "MB" in str(exc_info.value)

    def test_load_empty_json_object(self, temp_dir: Path) -> None:
        """Test loading an empty JSON object."""
        filepath = temp_dir / "empty.json"
        with open(filepath, "w") as f:
            f.write("{}")

        result = load_json(filepath)

        assert result == {}

    def test_load_json_array(self, temp_dir: Path) -> None:
        """Test loading a JSON array."""
        filepath = temp_dir / "array.json"
        with open(filepath, "w") as f:
            json.dump([1, 2, 3, "test", None], f)

        result = load_json(filepath)

        assert result == [1, 2, 3, "test", None]


# =============================================================================
# Test load_json_async
# =============================================================================


class TestLoadJsonAsync:
    """Tests for load_json_async function."""

    @pytest.mark.asyncio
    async def test_load_valid_json_file_async(
        self, temp_dir: Path, sample_json_data: Dict
    ) -> None:
        """Test loading a valid JSON file asynchronously."""
        filepath = temp_dir / "test.json"
        with open(filepath, "w") as f:
            json.dump(sample_json_data, f)

        result = await load_json_async(filepath)

        assert result == sample_json_data

    @pytest.mark.asyncio
    async def test_load_nonexistent_file_async_raises_error(
        self, temp_dir: Path
    ) -> None:
        """Test that loading a non-existent file asynchronously raises FileNotFoundError."""
        filepath = temp_dir / "nonexistent.json"

        with pytest.raises(FileNotFoundError):
            await load_json_async(filepath)

    @pytest.mark.asyncio
    async def test_load_invalid_json_async_raises_error(self, temp_dir: Path) -> None:
        """Test that loading invalid JSON asynchronously raises JSONDecodeError."""
        filepath = temp_dir / "invalid.json"
        with open(filepath, "w") as f:
            f.write("not valid json{{")

        with pytest.raises(json.JSONDecodeError):
            await load_json_async(filepath)

    @pytest.mark.asyncio
    async def test_load_large_file_async_raises_error(self, temp_dir: Path) -> None:
        """Test that loading a large file asynchronously raises ValueError."""
        filepath = temp_dir / "large.json"
        large_data = "x" * (MAX_FILE_SIZE + 1000)
        with open(filepath, "w") as f:
            f.write(f'"{large_data}"')

        with pytest.raises(ValueError) as exc_info:
            await load_json_async(filepath)

        assert "exceeds" in str(exc_info.value).lower()


# =============================================================================
# Test save_json
# =============================================================================


class TestSaveJson:
    """Tests for save_json function."""

    def test_save_json_creates_file(
        self, temp_dir: Path, sample_json_data: Dict
    ) -> None:
        """Test that saving JSON creates the file."""
        filepath = temp_dir / "output.json"

        save_json(filepath, sample_json_data)

        assert filepath.exists()
        with open(filepath) as f:
            loaded = json.load(f)
        assert loaded == sample_json_data

    def test_save_json_creates_parent_directories(self, temp_dir: Path) -> None:
        """Test that saving JSON creates parent directories if they don't exist."""
        filepath = temp_dir / "nested" / "deep" / "file.json"

        save_json(filepath, {"test": "data"})

        assert filepath.exists()
        assert filepath.parent.exists()

    def test_save_json_with_custom_indent(self, temp_dir: Path) -> None:
        """Test saving JSON with custom indentation."""
        filepath = temp_dir / "indented.json"
        data = {"key": "value"}

        save_json(filepath, data, indent=4)

        content = filepath.read_text()
        # Should have 4-space indentation
        assert '    "key"' in content

    def test_save_json_adds_trailing_newline(self, temp_dir: Path) -> None:
        """Test that saved JSON has trailing newline for POSIX compliance."""
        filepath = temp_dir / "newline.json"

        save_json(filepath, {"test": "data"})

        content = filepath.read_text()
        assert content.endswith("\n")

    def test_save_json_with_string_path(self, temp_dir: Path) -> None:
        """Test saving JSON using string path."""
        filepath = str(temp_dir / "string_path.json")

        save_json(filepath, {"test": "data"})

        assert Path(filepath).exists()

    def test_save_json_preserves_unicode(self, temp_dir: Path) -> None:
        """Test that saving JSON preserves unicode characters."""
        filepath = temp_dir / "unicode.json"
        data = {"message": "Hello 世界 🌍", "emoji": "🚀"}

        save_json(filepath, data)

        with open(filepath, encoding="utf-8") as f:
            loaded = json.load(f)
        assert loaded == data

    def test_save_json_non_serializable_raises_error(self, temp_dir: Path) -> None:
        """Test that saving non-serializable data raises TypeError."""
        filepath = temp_dir / "error.json"

        with pytest.raises(TypeError):
            save_json(filepath, {"data": object()})  # object() is not JSON serializable


# =============================================================================
# Test save_json_async
# =============================================================================


class TestSaveJsonAsync:
    """Tests for save_json_async function."""

    @pytest.mark.asyncio
    async def test_save_json_async_creates_file(self, temp_dir: Path) -> None:
        """Test that saving JSON asynchronously creates the file."""
        filepath = temp_dir / "async.json"
        data = {"test": "async data"}

        await save_json_async(filepath, data)

        assert filepath.exists()
        with open(filepath) as f:
            loaded = json.load(f)
        assert loaded == data

    @pytest.mark.asyncio
    async def test_save_json_async_creates_directories(self, temp_dir: Path) -> None:
        """Test that saving JSON asynchronously creates parent directories."""
        filepath = temp_dir / "a" / "b" / "c.json"

        await save_json_async(filepath, {"nested": True})

        assert filepath.exists()


# =============================================================================
# Test list_files
# =============================================================================


class TestListFiles:
    """Tests for list_files function."""

    def test_list_files_returns_sorted_list(self, temp_dir: Path) -> None:
        """Test that list_files returns a sorted list of filenames."""
        # Create files in non-alphabetical order
        (temp_dir / "zebra.json").write_text("{}")
        (temp_dir / "apple.json").write_text("{}")
        (temp_dir / "mango.json").write_text("{}")

        result = list_files(temp_dir)

        assert result == ["apple.json", "mango.json", "zebra.json"]

    def test_list_files_with_custom_pattern(self, temp_dir: Path) -> None:
        """Test listing files with a custom glob pattern."""
        (temp_dir / "test.json").write_text("{}")
        (temp_dir / "test.txt").write_text("")
        (temp_dir / "other.json").write_text("{}")

        result = list_files(temp_dir, pattern="*.txt")

        assert result == ["test.txt"]

    def test_list_files_nonexistent_directory_raises_error(
        self, temp_dir: Path
    ) -> None:
        """Test that listing a non-existent directory raises FileNotFoundError."""
        nonexistent = temp_dir / "does_not_exist"

        with pytest.raises(FileNotFoundError) as exc_info:
            list_files(nonexistent)

        assert "not found" in str(exc_info.value).lower()

    def test_list_files_on_file_raises_error(self, temp_dir: Path) -> None:
        """Test that listing a file (not directory) raises NotADirectoryError."""
        filepath = temp_dir / "not_a_dir.json"
        filepath.write_text("{}")

        with pytest.raises(NotADirectoryError) as exc_info:
            list_files(filepath)

        assert "not a directory" in str(exc_info.value).lower()

    def test_list_files_ignores_directories(self, temp_dir: Path) -> None:
        """Test that list_files ignores subdirectories."""
        (temp_dir / "file.json").write_text("{}")
        (temp_dir / "subdir").mkdir()
        (temp_dir / "subdir" / "nested.json").write_text("{}")

        result = list_files(temp_dir)

        assert result == ["file.json"]
        assert "subdir" not in result

    def test_list_files_empty_directory(self, temp_dir: Path) -> None:
        """Test that list_files returns empty list for empty directory."""
        result = list_files(temp_dir)

        assert result == []


# =============================================================================
# Test list_files_async
# =============================================================================


class TestListFilesAsync:
    """Tests for list_files_async function."""

    @pytest.mark.asyncio
    async def test_list_files_async_returns_sorted(self, temp_dir: Path) -> None:
        """Test that list_files_async returns a sorted list."""
        (temp_dir / "z.json").write_text("{}")
        (temp_dir / "a.json").write_text("{}")

        result = await list_files_async(temp_dir)

        assert result == ["a.json", "z.json"]

    @pytest.mark.asyncio
    async def test_list_files_async_nonexistent_raises_error(
        self, temp_dir: Path
    ) -> None:
        """Test that listing non-existent directory asynchronously raises error."""
        nonexistent = temp_dir / "missing"

        with pytest.raises(FileNotFoundError):
            await list_files_async(nonexistent)


# =============================================================================
# Test generate_id
# =============================================================================


class TestGenerateId:
    """Tests for generate_id function."""

    def test_generate_id_returns_32_char_hex(self) -> None:
        """Test that generate_id returns a 32-character hex string."""
        id1 = generate_id()

        assert len(id1) == 32
        assert all(c in "0123456789abcdef" for c in id1)

    def test_generate_id_returns_unique_values(self) -> None:
        """Test that generate_id returns unique values."""
        ids = [generate_id() for _ in range(100)]

        assert len(set(ids)) == 100

    def test_generate_id_no_dashes(self) -> None:
        """Test that generated IDs don't contain dashes."""
        id_value = generate_id()

        assert "-" not in id_value


# =============================================================================
# Test load_index / save_index
# =============================================================================


class TestIndexOperations:
    """Tests for index loading and saving operations."""

    def test_load_index_valid_collection(self, temp_dir: Path) -> None:
        """Test loading index for a valid collection."""
        # Create a mock collection directory with index
        collection_dir = temp_dir / "prompts"
        collection_dir.mkdir()
        index_data = {"items": [{"id": "123", "name": "Test"}], "version": 1}
        with open(collection_dir / "index.json", "w") as f:
            json.dump(index_data, f)

        with patch("mvp.services.storage.DATA_DIR", temp_dir):
            result = load_index("prompts")

        assert result == index_data

    def test_load_index_missing_file_returns_default(self, temp_dir: Path) -> None:
        """Test that loading missing index returns default empty structure."""
        collection_dir = temp_dir / "configs"
        collection_dir.mkdir()

        with patch("mvp.services.storage.DATA_DIR", temp_dir):
            result = load_index("configs")

        assert result == {"items": [], "version": 1}

    def test_load_index_invalid_collection_raises_error(self, temp_dir: Path) -> None:
        """Test that loading index for invalid collection raises ValueError."""
        with pytest.raises(ValueError) as exc_info:
            load_index("invalid_collection")

        assert "invalid collection" in str(exc_info.value).lower()
        assert "prompts" in str(exc_info.value)  # Should mention valid collections

    def test_save_index_valid_collection(self, temp_dir: Path) -> None:
        """Test saving index for a valid collection."""
        collection_dir = temp_dir / "runs"
        collection_dir.mkdir()
        index_data = {"items": [{"id": "456", "name": "Run 1"}], "version": 1}

        with patch("mvp.services.storage.DATA_DIR", temp_dir):
            save_index("runs", index_data)

        # Verify file was created
        index_file = collection_dir / "index.json"
        assert index_file.exists()
        with open(index_file) as f:
            loaded = json.load(f)
        assert loaded == index_data

    def test_save_index_invalid_collection_raises_error(self, temp_dir: Path) -> None:
        """Test that saving index for invalid collection raises ValueError."""
        with pytest.raises(ValueError) as exc_info:
            save_index("invalid", {"items": []})

        assert "invalid collection" in str(exc_info.value).lower()

    def test_save_and_load_roundtrip(self, temp_dir: Path) -> None:
        """Test that save_index and load_index work together."""
        collection_dir = temp_dir / "prompts"
        collection_dir.mkdir()
        original_data = {
            "items": [
                {"id": "1", "name": "Prompt A"},
                {"id": "2", "name": "Prompt B"},
            ],
            "version": 1,
        }

        with patch("mvp.services.storage.DATA_DIR", temp_dir):
            save_index("prompts", original_data)
            loaded = load_index("prompts")

        assert loaded == original_data


# =============================================================================
# Test load_index_async / save_index_async
# =============================================================================


class TestIndexOperationsAsync:
    """Tests for async index operations."""

    @pytest.mark.asyncio
    async def test_load_index_async_valid_collection(self, temp_dir: Path) -> None:
        """Test loading index asynchronously for a valid collection."""
        collection_dir = temp_dir / "prompts"
        collection_dir.mkdir()
        index_data = {"items": [{"id": "123", "name": "Test"}], "version": 1}
        with open(collection_dir / "index.json", "w") as f:
            json.dump(index_data, f)

        with patch("mvp.services.storage.DATA_DIR", temp_dir):
            result = await load_index_async("prompts")

        assert result == index_data

    @pytest.mark.asyncio
    async def test_load_index_async_missing_returns_default(
        self, temp_dir: Path
    ) -> None:
        """Test that async loading missing index returns default."""
        collection_dir = temp_dir / "configs"
        collection_dir.mkdir()

        with patch("mvp.services.storage.DATA_DIR", temp_dir):
            result = await load_index_async("configs")

        assert result == {"items": [], "version": 1}

    @pytest.mark.asyncio
    async def test_save_index_async_valid_collection(self, temp_dir: Path) -> None:
        """Test saving index asynchronously for a valid collection."""
        collection_dir = temp_dir / "runs"
        collection_dir.mkdir()
        index_data = {"items": [{"id": "789", "name": "Async Run"}], "version": 1}

        with patch("mvp.services.storage.DATA_DIR", temp_dir):
            await save_index_async("runs", index_data)

        index_file = collection_dir / "index.json"
        assert index_file.exists()


# =============================================================================
# Test get_collection_path
# =============================================================================


class TestGetCollectionPath:
    """Tests for get_collection_path function."""

    def test_get_collection_path_valid_collections(self, temp_dir: Path) -> None:
        """Test getting path for all valid collections."""
        with patch("mvp.services.storage.DATA_DIR", temp_dir):
            for collection in COLLECTIONS:
                path = get_collection_path(collection)
                assert path == temp_dir / collection
                assert path.name == collection

    def test_get_collection_path_invalid_raises_error(self) -> None:
        """Test that getting path for invalid collection raises ValueError."""
        with pytest.raises(ValueError) as exc_info:
            get_collection_path("not_a_collection")

        assert "invalid collection" in str(exc_info.value).lower()

    def test_get_collection_dir_alias(self, temp_dir: Path) -> None:
        """Test that get_collection_dir is an alias for get_collection_path."""
        from mvp.services.storage import get_collection_dir

        with patch("mvp.services.storage.DATA_DIR", temp_dir):
            path1 = get_collection_path("prompts")
            path2 = get_collection_dir("prompts")
            assert path1 == path2


# =============================================================================
# Integration Tests
# =============================================================================


class TestStorageIntegration:
    """Integration tests for storage service operations."""

    def test_full_workflow_save_and_load(self, temp_dir: Path) -> None:
        """Test a full workflow: save, list, load, delete cycle."""
        # Save multiple files
        files = []
        for i in range(5):
            filepath = temp_dir / f"file_{i:02d}.json"
            save_json(filepath, {"index": i, "data": f"value_{i}"})
            files.append(filepath)

        # List files
        listed = list_files(temp_dir)
        assert len(listed) == 5
        assert listed == [f"file_{i:02d}.json" for i in range(5)]

        # Load each file
        for i, filename in enumerate(listed):
            data = load_json(temp_dir / filename)
            assert data["index"] == i

    def test_concurrent_file_operations(self, temp_dir: Path) -> None:
        """Test that multiple files can be saved and loaded independently."""
        import asyncio

        async def save_and_verify(index: int) -> bool:
            filepath = temp_dir / f"concurrent_{index}.json"
            data = {"id": index, "timestamp": index * 1000}
            await save_json_async(filepath, data)
            loaded = await load_json_async(filepath)
            return loaded == data

        async def run_all():
            tasks = [save_and_verify(i) for i in range(10)]
            return await asyncio.gather(*tasks)

        results = asyncio.run(run_all())
        assert all(results)

    def test_file_permissions_error(self, temp_dir: Path) -> None:
        """Test handling of permission errors."""
        # Create a read-only directory
        readonly_dir = temp_dir / "readonly"
        readonly_dir.mkdir()

        # Skip on Windows as permissions work differently
        if os.name != "nt":
            readonly_dir.chmod(0o555)  # Read and execute, no write

            try:
                filepath = readonly_dir / "test.json"
                with pytest.raises(PermissionError):
                    save_json(filepath, {"test": "data"})
            finally:
                # Restore permissions for cleanup
                readonly_dir.chmod(0o755)
