"""Run execution service for prompt governor MVP.

This module provides utilities for executing extraction runs, including:
- Loading ground truth data
- Building model API parameters from configurations
- Executing extraction pipelines
- Managing run status and results

This module integrates with the prompt_optimization codebase for real extraction.
"""

import json
import os
import sys
import time
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from mvp.models.config import ModelConfig
from mvp.models.prompt import PromptVersion
from mvp.models.run import Run
from mvp.services.metrics import calculate_cost, calculate_metrics, extract_token_usage
from mvp.services.storage import generate_id, load_json, save_json

# Ensure prompt_optimization is in path for Docker environment
PROMPT_OPT_DIR = Path("/app/prompt_optimization")
if str(PROMPT_OPT_DIR) not in sys.path:
    sys.path.insert(0, str(PROMPT_OPT_DIR))

# Pipeline integration imports (from prompt_optimization codebase)
try:
    from pipelines.modular_pipeline import ModularPipeline
    from schemas.contract import Contract
    from utils.openrouter_client import estimate_cost as estimate_openrouter_cost
    from utils.recall_metrics import calculate_recall_accuracy

    PIPELINE_AVAILABLE = True
except ImportError as _pipeline_import_error:
    PIPELINE_AVAILABLE = False
    PIPELINE_ERROR = str(_pipeline_import_error)

# Ground truth directory (mounted in Docker)
GROUND_TRUTH_DIR = Path("/app/ground_truth")

# Data collections directory
DATA_DIR = Path(__file__).parent.parent.parent / "data"


class ExecutorError(Exception):
    """Base exception for executor service errors."""

    pass


class GroundTruthNotFoundError(ExecutorError):
    """Raised when ground truth file is not found."""

    pass


class PromptNotFoundError(ExecutorError):
    """Raised when prompt is not found in storage."""

    pass


class ConfigNotFoundError(ExecutorError):
    """Raised when config is not found in storage."""

    pass


class DocumentNotFoundError(ExecutorError):
    """Raised when document is not found."""

    pass


class ExtractionError(ExecutorError):
    """Raised when extraction pipeline fails."""

    pass


class PipelineNotAvailableError(ExecutorError):
    """Raised when extraction pipeline is not available (import failed)."""

    pass


class SchemaValidationError(ExecutorError):
    """Raised when extraction output fails schema validation."""

    pass


def load_ground_truth(document_name: str) -> Dict:
    """Load ground truth data from file.

    Args:
        document_name: Name of the document (e.g., 'contract_001').
            The file will be loaded from /app/ground_truth/{document_name}.json

    Returns:
        Parsed JSON ground truth data.

    Raises:
        GroundTruthNotFoundError: If the ground truth file doesn't exist.
        json.JSONDecodeError: If the file contains invalid JSON.

    Example:
        >>> ground_truth = load_ground_truth("annual_report_2023")
        >>> print(ground_truth["company_name"])
        'Acme Corp'
    """
    # Handle extension if provided
    if document_name.endswith(".json"):
        document_name = document_name[:-5]

    gt_path = GROUND_TRUTH_DIR / f"{document_name}.json"

    try:
        return load_json(gt_path)
    except FileNotFoundError as e:
        raise GroundTruthNotFoundError(
            f"Ground truth not found for document '{document_name}'"
        ) from e


def build_model_params(config: ModelConfig) -> Dict:
    """Convert ModelConfig to API parameters dictionary.

    Converts a ModelConfig instance into provider-specific API parameters
    for OpenAI, Anthropic, or OpenRouter.

    Args:
        config: ModelConfig instance containing model parameters.

    Returns:
        Dictionary of API parameters for the configured provider.

    Example:
        >>> config = ModelConfig(
        ...     name="GPT-4 Test",
        ...     provider="openai",
        ...     model_id="gpt-4",
        ...     temperature=0.7,
        ...     max_tokens=2048,
        ...     reasoning_effort="medium"
        ... )
        >>> params = build_model_params(config)
        >>> print(params["model"])
        'gpt-4'
    """
    # Base parameters common to all providers
    params = {
        "model": config.model_id,
        "temperature": config.temperature,
    }

    # Add optional parameters if set
    if config.max_tokens is not None:
        params["max_tokens"] = config.max_tokens

    # Provider-specific parameter handling
    if config.provider == "openai":
        # OpenAI supports reasoning_effort for o1 models
        if config.reasoning_effort and config.model_id.startswith("o1"):
            params["reasoning_effort"] = config.reasoning_effort

        # Add extra_params last to allow overrides
        params.update(config.extra_params)

    elif config.provider == "anthropic":
        # Anthropic uses max_tokens (required), not max_completion_tokens
        # Anthropic doesn't support reasoning_effort parameter
        if config.reasoning_effort:
            # Add as metadata in extra_headers for tracking
            params["extra_headers"] = {
                "anthropic-reasoning-effort": config.reasoning_effort
            }

        # Add extra_params
        params.update(config.extra_params)

    elif config.provider == "openrouter":
        # OpenRouter supports additional parameters
        if config.reasoning_effort:
            params["reasoning"] = {"effort": config.reasoning_effort}

        # Add extra_params (OpenRouter specific)
        params.update(config.extra_params)

    return params


def _load_prompt(prompt_id: str) -> PromptVersion:
    """Load a prompt version from storage.

    Args:
        prompt_id: UUID string of the prompt to load.

    Returns:
        PromptVersion instance.

    Raises:
        PromptNotFoundError: If the prompt doesn't exist.
    """
    prompts_dir = DATA_DIR / "prompts"
    prompt_path = prompts_dir / f"{prompt_id}.json"

    try:
        data = load_json(prompt_path)
        return PromptVersion(**data)
    except FileNotFoundError as e:
        raise PromptNotFoundError(f"Prompt not found: {prompt_id}") from e


def _load_config(config_id: str) -> ModelConfig:
    """Load a model config from storage.

    Args:
        config_id: UUID string of the config to load.

    Returns:
        ModelConfig instance.

    Raises:
        ConfigNotFoundError: If the config doesn't exist.
    """
    configs_dir = DATA_DIR / "configs"
    config_path = configs_dir / f"{config_id}.json"

    try:
        data = load_json(config_path)
        return ModelConfig(**data)
    except FileNotFoundError as e:
        raise ConfigNotFoundError(f"Config not found: {config_id}") from e


def _load_document(document_name: str) -> str:
    """Load document content from the documents directory.

    Args:
        document_name: Name of the document file.

    Returns:
        Document content as string.

    Raises:
        DocumentNotFoundError: If the document doesn't exist.
    """
    documents_dir = Path("/app/documents")

    # Try exact name first
    doc_path = documents_dir / document_name

    # If not found and no extension, try common extensions
    if not doc_path.exists() and "." not in document_name:
        for ext in [".pdf", ".txt", ".md", ".docx"]:
            alt_path = documents_dir / f"{document_name}{ext}"
            if alt_path.exists():
                doc_path = alt_path
                break

    if not doc_path.exists():
        raise DocumentNotFoundError(f"Document not found: {document_name}")

    # Read as text for now (PDF would need OCR processing in real implementation)
    try:
        with open(doc_path, "r", encoding="utf-8") as f:
            return f.read()
    except UnicodeDecodeError:
        # Binary file (PDF, etc.) - return placeholder for now
        # In production, this would trigger OCR processing
        return f"[Binary document: {document_name}]"


def _save_run(run: Run) -> None:
    """Save a run to storage.

    Args:
        run: Run instance to save.
    """
    runs_dir = DATA_DIR / "runs"
    run_path = runs_dir / f"{run.id}.json"

    # Convert to dict and save
    run_data = json.loads(run.model_dump_json())
    save_json(run_path, run_data)


def _execute_extraction_placeholder(
    prompt: PromptVersion, config: ModelConfig, document_content: str
) -> Dict:
    """Placeholder for the actual extraction pipeline.

    This function simulates what the real extraction pipeline would do:
    - Format the prompt with the document content
    - Call the LLM API
    - Parse and validate the response
    - Return the extraction result

    Args:
        prompt: PromptVersion with blocks to use.
        config: ModelConfig with API parameters.
        document_content: Content of the document to extract from.

    Returns:
        Dictionary containing:
            - output: The extracted data
            - tokens: Token usage dict with 'input', 'output', 'total'
            - latency_ms: Request latency in milliseconds
            - raw_response: Raw API response for token extraction

    Note:
        This is a placeholder implementation. Replace with actual
        extract_modular_contract() call from the pipeline.
    """
    # Simulate API call latency
    start_time = time.time()
    time.sleep(0.1)  # 100ms simulated latency
    end_time = time.time()

    # Simulated extraction output (placeholder)
    simulated_output = {
        "extracted_data": {
            "document_type": "placeholder",
            "fields_found": 0,
            "processing_status": "simulated",
        },
        "note": "This is a placeholder extraction. Replace with actual pipeline integration.",
    }

    # Simulated token usage (would come from actual API response)
    simulated_tokens = {
        "input": len(document_content) // 4,  # Rough estimate: 4 chars per token
        "output": 500,  # Simulated output tokens
        "total": len(document_content) // 4 + 500,
    }

    # Simulated API response for token extraction
    simulated_response = {
        "usage": {
            "prompt_tokens": simulated_tokens["input"],
            "completion_tokens": simulated_tokens["output"],
            "total_tokens": simulated_tokens["total"],
        }
    }

    latency_ms = int((end_time - start_time) * 1000)

    return {
        "output": simulated_output,
        "tokens": simulated_tokens,
        "latency_ms": latency_ms,
        "raw_response": simulated_response,
    }


def execute_run(run_id: str, prompt_id: str, config_id: str, document_name: str) -> Run:
    """Execute an extraction run.

    This is the main execution function that:
    1. Loads the prompt, config, and document
    2. Updates run status to "running"
    3. Executes the extraction pipeline (placeholder)
    4. Loads ground truth and calculates metrics
    5. Updates run with output, metrics, cost, and tokens
    6. Sets final status to "completed" or "failed"
    7. Saves the run to storage

    Args:
        run_id: UUID string of the run to execute.
        prompt_id: UUID string of the prompt version to use.
        config_id: UUID string of the model config to use.
        document_name: Name of the document to process.

    Returns:
        Updated Run instance with results.

    Raises:
        ExecutorError: If any step of execution fails.

    Example:
        >>> run = execute_run(
        ...     run_id="abc123...",
        ...     prompt_id="def456...",
        ...     config_id="ghi789...",
        ...     document_name="contract_001"
        ... )
        >>> print(run.status)
        'completed'
        >>> print(run.metrics["recall"])
        0.85
    """
    # Load existing run or create new one
    try:
        run = _load_run(run_id)
    except FileNotFoundError:
        # Run doesn't exist yet, will be created fresh
        run = Run(
            id=uuid.UUID(run_id) if isinstance(run_id, str) else run_id,
            prompt_id=uuid.UUID(prompt_id) if isinstance(prompt_id, str) else prompt_id,
            config_id=uuid.UUID(config_id) if isinstance(config_id, str) else config_id,
            document_name=document_name,
            status="pending",
        )

    # Step 1: Load required resources
    try:
        prompt = _load_prompt(prompt_id)
        config = _load_config(config_id)
        document_content = _load_document(document_name)
        ground_truth = load_ground_truth(document_name)
    except ExecutorError:
        raise
    except Exception as e:
        run.status = "failed"
        run.completed_at = datetime.utcnow()
        _save_run(run)
        raise ExecutorError(f"Failed to load resources: {e}") from e

    # Step 2: Update status to running
    run.status = "running"
    run.started_at = datetime.utcnow()
    _save_run(run)

    try:
        # Step 3: Execute extraction (placeholder)
        result = _execute_extraction_placeholder(prompt, config, document_content)

        # Step 4: Calculate metrics
        output = result["output"]
        metrics = calculate_metrics(output, ground_truth)
        metrics["latency_ms"] = result["latency_ms"]

        # Step 5: Calculate cost
        tokens = result["tokens"]
        cost = calculate_cost(tokens, config)

        # Step 6: Update run with results
        run.output = output
        run.metrics = metrics
        run.tokens = tokens
        run.cost_usd = cost
        run.status = "completed"
        run.completed_at = datetime.utcnow()

    except Exception as e:
        # Mark as failed on any error
        run.status = "failed"
        run.completed_at = datetime.utcnow()
        run.output = {"error": str(e)}
        _save_run(run)
        raise ExtractionError(f"Extraction failed: {e}") from e

    # Step 7: Save final run
    _save_run(run)

    return run


def _load_run(run_id: str) -> Run:
    """Load a run from storage.

    Args:
        run_id: UUID string of the run to load.

    Returns:
        Run instance.

    Raises:
        FileNotFoundError: If the run doesn't exist.
    """
    runs_dir = DATA_DIR / "runs"
    run_path = runs_dir / f"{run_id}.json"

    data = load_json(run_path)
    return Run(**data)


def create_run(prompt_id_str: str, config_id_str: str, document_name: str) -> Run:
    """Create a new run with pending status.

    Creates a new Run instance and saves it to storage with "pending" status.
    The run can then be executed using execute_run().

    Args:
        prompt_id_str: UUID string of the prompt version to use.
        config_id_str: UUID string of the model config to use.
        document_name: Name of the document to process.

    Returns:
        New Run instance with pending status.

    Example:
        >>> run = create_run(
        ...     prompt_id_str="def456...",
        ...     config_id_str="ghi789...",
        ...     document_name="contract_001"
        ... )
        >>> print(run.status)
        'pending'
        >>> # Later, execute it
        >>> executed_run = execute_run(str(run.id), prompt_id_str, config_id_str, document_name)
    """
    # Convert string IDs to UUID objects
    prompt_id = uuid.UUID(prompt_id_str)
    config_id = uuid.UUID(config_id_str)

    # Create new run with pending status
    run = Run(
        prompt_id=prompt_id,
        config_id=config_id,
        document_name=document_name,
        status="pending",
    )

    # Save to storage
    _save_run(run)

    return run
