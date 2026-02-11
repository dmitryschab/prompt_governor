"""Metrics calculation service for prompt optimization evaluation.

This module provides utilities for calculating extraction metrics (recall, precision, F1),
cost estimation based on token usage, and extracting token counts from API responses.
"""

from typing import Dict, List, Optional, Set, Any
from mvp.models.config import ModelConfig


# Model pricing per 1K tokens (input, output) in USD
# Prices are approximate and may need updating as providers change pricing
MODEL_PRICING = {
    # OpenAI models
    "gpt-4": {"input": 0.03, "output": 0.06},
    "gpt-4-turbo": {"input": 0.01, "output": 0.03},
    "gpt-4-turbo-preview": {"input": 0.01, "output": 0.03},
    "gpt-4o": {"input": 0.005, "output": 0.015},
    "gpt-4o-mini": {"input": 0.00015, "output": 0.0006},
    "gpt-3.5-turbo": {"input": 0.0005, "output": 0.0015},
    "gpt-3.5-turbo-0125": {"input": 0.0005, "output": 0.0015},
    # Anthropic models
    "claude-3-opus": {"input": 0.015, "output": 0.075},
    "claude-3-opus-20240229": {"input": 0.015, "output": 0.075},
    "claude-3-sonnet": {"input": 0.003, "output": 0.015},
    "claude-3-sonnet-20240229": {"input": 0.003, "output": 0.015},
    "claude-3-haiku": {"input": 0.00025, "output": 0.00125},
    "claude-3-haiku-20240307": {"input": 0.00025, "output": 0.00125},
    # Legacy GPT-3.5
    "text-davinci-003": {"input": 0.02, "output": 0.02},
}


def _normalize_field_name(field: str) -> str:
    """Normalize field name for comparison (lowercase, strip whitespace).

    Args:
        field: Field name to normalize.

    Returns:
        Normalized field name.
    """
    return field.lower().strip()


def _get_all_fields(data: Dict, prefix: str = "") -> Set[str]:
    """Recursively extract all field paths from a nested dictionary.

    Args:
        data: Dictionary to extract fields from.
        prefix: Current path prefix for nested fields.

    Returns:
        Set of field paths in dot notation (e.g., "user.name").
    """
    fields = set()
    for key, value in data.items():
        field_path = f"{prefix}.{key}" if prefix else key
        fields.add(_normalize_field_name(field_path))
        if isinstance(value, dict):
            fields.update(_get_all_fields(value, field_path))
    return fields


def calculate_metrics(output: Dict, ground_truth: Dict) -> Dict:
    """Compare extracted output against ground truth and calculate metrics.

    Calculates recall, precision, and F1 score based on field-level matching.
    Fields are compared in a case-insensitive manner.

    Args:
        output: The extracted output from the model (nested dict structure).
        ground_truth: The expected ground truth (nested dict structure).

    Returns:
        Dictionary containing:
            - recall: Float between 0 and 1 (matched / total_gt_fields)
            - precision: Float between 0 and 1 (matched / total_output_fields)
            - f1: Float between 0 and 1 (2 * precision * recall / (precision + recall))
            - missing_fields: List of field paths present in ground_truth but missing in output
            - total_gt_fields: Total number of fields in ground_truth
            - total_output_fields: Total number of fields in output
            - matched_fields: Number of fields present in both

    Example:
        >>> output = {"name": "John", "age": 30}
        >>> ground_truth = {"name": "John", "age": 30, "email": "john@example.com"}
        >>> metrics = calculate_metrics(output, ground_truth)
        >>> print(metrics["recall"])
        0.666666...
    """
    # Get all field paths from both dictionaries
    output_fields = _get_all_fields(output)
    gt_fields = _get_all_fields(ground_truth)

    # Calculate matches
    matched_fields = output_fields & gt_fields
    missing_fields = sorted(list(gt_fields - output_fields))
    extra_fields = sorted(list(output_fields - gt_fields))

    # Calculate metrics
    total_gt_fields = len(gt_fields)
    total_output_fields = len(output_fields)
    matched_count = len(matched_fields)

    # Recall: matched / total ground truth fields
    recall = matched_count / total_gt_fields if total_gt_fields > 0 else 0.0

    # Precision: matched / total output fields
    precision = matched_count / total_output_fields if total_output_fields > 0 else 0.0

    # F1 Score: harmonic mean of precision and recall
    if precision + recall > 0:
        f1 = 2 * (precision * recall) / (precision + recall)
    else:
        f1 = 0.0

    return {
        "recall": round(recall, 6),
        "precision": round(precision, 6),
        "f1": round(f1, 6),
        "missing_fields": missing_fields,
        "extra_fields": extra_fields,
        "total_gt_fields": total_gt_fields,
        "total_output_fields": total_output_fields,
        "matched_fields": matched_count,
    }


def calculate_cost(tokens: Dict[str, int], model_config: ModelConfig) -> float:
    """Estimate cost based on input/output tokens and model pricing.

    Args:
        tokens: Dictionary with 'input' and 'output' token counts.
               Example: {"input": 1000, "output": 500}
        model_config: ModelConfig instance containing model_id for pricing lookup.

    Returns:
        Estimated cost in USD.

    Example:
        >>> model_config = ModelConfig(
        ...     name="Test",
        ...     provider="openai",
        ...     model_id="gpt-4"
        ... )
        >>> tokens = {"input": 2000, "output": 1000}
        >>> cost = calculate_cost(tokens, model_config)
        >>> print(f"${cost:.4f}")
        $0.1200

    Note:
        If model_id is not found in pricing table, returns 0.0 and logs a warning.
    """
    model_id = model_config.model_id

    # Look up pricing for the model
    pricing = MODEL_PRICING.get(model_id)

    if pricing is None:
        # Try to find a partial match (e.g., "gpt-4-0613" matches "gpt-4")
        for known_model, known_pricing in MODEL_PRICING.items():
            if model_id.startswith(known_model) or known_model in model_id:
                pricing = known_pricing
                break

    if pricing is None:
        # Unknown model - return 0 cost
        return 0.0

    input_tokens = tokens.get("input", 0)
    output_tokens = tokens.get("output", 0)

    # Calculate cost: (tokens / 1000) * price_per_1k
    input_cost = (input_tokens / 1000) * pricing["input"]
    output_cost = (output_tokens / 1000) * pricing["output"]

    total_cost = input_cost + output_cost

    return round(total_cost, 6)


def extract_token_usage(response: Dict[str, Any]) -> Dict[str, int]:
    """Extract token counts from API response.

    Supports both OpenAI and Anthropic response formats.

    Args:
        response: API response dictionary from OpenAI or Anthropic.

    Returns:
        Dictionary containing:
            - input: Number of input/prompt tokens
            - output: Number of output/completion tokens
            - total: Total tokens used

    Example:
        >>> # OpenAI format
        >>> response = {
        ...     "usage": {
        ...         "prompt_tokens": 100,
        ...         "completion_tokens": 50,
        ...         "total_tokens": 150
        ...     }
        ... }
        >>> tokens = extract_token_usage(response)
        >>> print(tokens)
        {'input': 100, 'output': 50, 'total': 150}

        >>> # Anthropic format
        >>> response = {
        ...     "usage": {
        ...         "input_tokens": 200,
        ...         "output_tokens": 100
        ...     }
        ... }
        >>> tokens = extract_token_usage(response)
        >>> print(tokens)
        {'input': 200, 'output': 100, 'total': 300}
    """
    usage = response.get("usage", {})

    # OpenAI format
    if "prompt_tokens" in usage:
        input_tokens = usage.get("prompt_tokens", 0)
        output_tokens = usage.get("completion_tokens", 0)
        total_tokens = usage.get("total_tokens", input_tokens + output_tokens)
    # Anthropic format
    elif "input_tokens" in usage:
        input_tokens = usage.get("input_tokens", 0)
        output_tokens = usage.get("output_tokens", 0)
        total_tokens = input_tokens + output_tokens
    # Legacy or unknown format - try common keys
    else:
        input_tokens = usage.get("input", 0)
        output_tokens = usage.get("output", 0)
        total_tokens = usage.get("total", input_tokens + output_tokens)

    return {
        "input": int(input_tokens),
        "output": int(output_tokens),
        "total": int(total_tokens),
    }
