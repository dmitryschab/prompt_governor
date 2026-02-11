"""Unit tests for the metrics service.

Tests metrics calculation, cost estimation, and token extraction including:
- Recall, precision, and F1 calculation
- Nested field comparison
- Cost calculation for different models
- Token usage extraction from OpenAI and Anthropic responses
- Edge cases (empty data, missing fields)
"""

from typing import Any, Dict, List
from unittest.mock import patch

import pytest
from pytest import approx

from mvp.models.config import ModelConfig
from mvp.services.metrics import (
    MODEL_PRICING,
    calculate_cost,
    calculate_metrics,
    extract_token_usage,
)


# =============================================================================
# Test calculate_metrics
# =============================================================================


class TestCalculateMetrics:
    """Tests for calculate_metrics function."""

    def test_perfect_match(self) -> None:
        """Test metrics when output exactly matches ground truth."""
        output = {"name": "John", "age": 30}
        ground_truth = {"name": "John", "age": 30}

        result = calculate_metrics(output, ground_truth)

        assert result["recall"] == 1.0
        assert result["precision"] == 1.0
        assert result["f1"] == 1.0
        assert result["matched_fields"] == 2
        assert result["missing_fields"] == []
        assert result["extra_fields"] == []

    def test_partial_match(self) -> None:
        """Test metrics with partial field matches."""
        output = {"name": "John"}
        ground_truth = {"name": "John", "age": 30, "city": "NYC"}

        result = calculate_metrics(output, ground_truth)

        assert result["recall"] == approx(1 / 3)
        assert result["precision"] == 1.0  # All output fields matched
        assert result["matched_fields"] == 1
        assert result["missing_fields"] == ["age", "city"]
        assert result["extra_fields"] == []

    def test_extra_fields_in_output(self) -> None:
        """Test when output has extra fields not in ground truth."""
        output = {"name": "John", "age": 30, "email": "john@example.com"}
        ground_truth = {"name": "John", "age": 30}

        result = calculate_metrics(output, ground_truth)

        assert result["recall"] == 1.0
        assert result["precision"] == approx(2 / 3)  # 2 matched out of 3 output fields
        assert result["extra_fields"] == ["email"]
        assert result["missing_fields"] == []

    def test_case_insensitive_matching(self) -> None:
        """Test that field names are compared case-insensitively."""
        output = {"Name": "John", "AGE": 30}
        ground_truth = {"name": "John", "age": 30}

        result = calculate_metrics(output, ground_truth)

        assert result["recall"] == 1.0
        assert result["precision"] == 1.0
        assert result["matched_fields"] == 2

    def test_whitespace_normalization(self) -> None:
        """Test that whitespace is normalized in field names."""
        output = {"  name  ": "John", " age ": 30}
        ground_truth = {"name": "John", "age": 30}

        result = calculate_metrics(output, ground_truth)

        assert result["recall"] == 1.0
        assert result["precision"] == 1.0

    def test_empty_output(self) -> None:
        """Test metrics with empty output."""
        output = {}
        ground_truth = {"name": "John", "age": 30}

        result = calculate_metrics(output, ground_truth)

        assert result["recall"] == 0.0
        assert result["precision"] == 0.0  # No output fields to match
        assert result["f1"] == 0.0
        assert result["matched_fields"] == 0
        assert result["missing_fields"] == ["age", "name"]

    def test_empty_ground_truth(self) -> None:
        """Test metrics with empty ground truth."""
        output = {"name": "John", "age": 30}
        ground_truth = {}

        result = calculate_metrics(output, ground_truth)

        assert result["recall"] == 0.0  # Nothing to match against
        assert result["precision"] == 0.0  # Output fields don't match anything
        assert result["f1"] == 0.0
        assert result["total_gt_fields"] == 0

    def test_both_empty(self) -> None:
        """Test metrics when both output and ground truth are empty."""
        output = {}
        ground_truth = {}

        result = calculate_metrics(output, ground_truth)

        assert result["recall"] == 0.0
        assert result["precision"] == 0.0
        assert result["f1"] == 0.0
        assert result["matched_fields"] == 0

    def test_nested_fields_simple(self) -> None:
        """Test metrics with simple nested objects."""
        output = {"user": {"name": "John", "age": 30}}
        ground_truth = {"user": {"name": "John", "age": 30}}

        result = calculate_metrics(output, ground_truth)

        assert result["recall"] == 1.0
        assert result["precision"] == 1.0
        assert result["total_gt_fields"] == 3  # user, user.name, user.age

    def test_nested_fields_partial_match(self) -> None:
        """Test metrics with partially matching nested objects."""
        output = {"user": {"name": "John"}}
        ground_truth = {"user": {"name": "John", "age": 30}}

        result = calculate_metrics(output, ground_truth)

        assert result["recall"] == approx(2 / 3)  # user, user.name matched
        assert result["precision"] == 1.0
        assert "user.age" in result["missing_fields"]

    def test_deeply_nested_fields(self) -> None:
        """Test metrics with deeply nested structures."""
        output = {"a": {"b": {"c": {"d": "value"}}}}
        ground_truth = {"a": {"b": {"c": {"d": "value", "e": "other"}}}}

        result = calculate_metrics(output, ground_truth)

        assert result["recall"] == 4 / 5  # 4 matched out of 5 total
        assert "a.b.c.e" in result["missing_fields"]

    def test_mixed_nesting(self) -> None:
        """Test metrics with mixed nested and flat structures."""
        output = {
            "flat_field": "value1",
            "nested": {"inner": "value2"},
        }
        ground_truth = {
            "flat_field": "value1",
            "nested": {"inner": "value2", "missing": "value3"},
            "other": "value4",
        }

        result = calculate_metrics(output, ground_truth)

        assert result["total_gt_fields"] == 5
        assert result["total_output_fields"] == 3
        assert result["matched_fields"] == 3
        assert "nested.missing" in result["missing_fields"]
        assert "other" in result["missing_fields"]

    def test_complex_insurance_contract(self) -> None:
        """Test with complex insurance contract structure."""
        output = {
            "contract": {
                "number": "CNT-2024-001",
                "parties": {
                    "insurer": "ABC Insurance",
                    "insured": "XYZ Corp",
                },
            },
            "coverage": {
                "limit": 1000000,
            },
        }
        ground_truth = {
            "contract": {
                "number": "CNT-2024-001",
                "parties": {
                    "insurer": "ABC Insurance",
                    "insured": "XYZ Corp",
                    "broker": "Broker Inc",
                },
                "start_date": "2024-01-01",
            },
            "coverage": {
                "limit": 1000000,
                "deductible": 5000,
            },
        }

        result = calculate_metrics(output, ground_truth)

        # Fields: contract, contract.number, contract.parties, contract.parties.insurer,
        # contract.parties.insured, coverage, coverage.limit = 7 output fields
        # Plus: contract.parties.broker, contract.start_date, coverage.deductible = 3 missing
        assert result["total_output_fields"] == 7
        assert result["total_gt_fields"] == 10
        assert result["matched_fields"] == 7
        assert result["recall"] == 0.7
        assert result["precision"] == 1.0

    def test_f1_calculation(self) -> None:
        """Test F1 score calculation with known values."""
        # Recall = 0.5, Precision = 0.5
        # F1 = 2 * (0.5 * 0.5) / (0.5 + 0.5) = 0.5
        output = {"a": 1, "b": 2}
        ground_truth = {"a": 1, "c": 3}

        result = calculate_metrics(output, ground_truth)

        assert result["recall"] == 0.5
        assert result["precision"] == 0.5
        assert result["f1"] == 0.5

    def test_f1_with_zero_precision_recall(self) -> None:
        """Test F1 when precision and recall are both zero."""
        output = {"a": 1}
        ground_truth = {"b": 2}

        result = calculate_metrics(output, ground_truth)

        assert result["precision"] == 0.0
        assert result["recall"] == 0.0
        assert result["f1"] == 0.0  # Should not divide by zero

    def test_returned_fields_are_sorted(self) -> None:
        """Test that missing_fields and extra_fields are sorted."""
        output = {"z": 1, "a": 2, "m": 3}
        ground_truth = {"x": 1, "b": 2}

        result = calculate_metrics(output, ground_truth)

        assert result["missing_fields"] == ["b", "x"]
        assert result["extra_fields"] == ["a", "m", "z"]

    def test_metric_values_are_rounded(self) -> None:
        """Test that metric values are properly rounded to 6 decimal places."""
        output = {"a": 1}
        ground_truth = {"a": 1, "b": 2, "c": 3}

        result = calculate_metrics(output, ground_truth)

        # Recall = 1/3 = 0.3333333333...
        assert result["recall"] == 0.333333
        # Check it's exactly 6 decimal places
        assert len(str(result["recall"]).split(".")[1]) == 6


# =============================================================================
# Test calculate_cost
# =============================================================================


class TestCalculateCost:
    """Tests for calculate_cost function."""

    @pytest.fixture
    def openai_config(self) -> ModelConfig:
        """Create an OpenAI model config."""
        return ModelConfig(
            name="Test OpenAI",
            provider="openai",
            model_id="gpt-4",
        )

    @pytest.fixture
    def anthropic_config(self) -> ModelConfig:
        """Create an Anthropic model config."""
        return ModelConfig(
            name="Test Anthropic",
            provider="anthropic",
            model_id="claude-3-opus",
        )

    def test_calculate_cost_openai_gpt4(self, openai_config: ModelConfig) -> None:
        """Test cost calculation for GPT-4."""
        tokens = {"input": 1000, "output": 500}

        cost = calculate_cost(tokens, openai_config)

        # GPT-4 pricing: input $0.03/1K, output $0.06/1K
        # Cost = (1000/1000)*0.03 + (500/1000)*0.06 = 0.03 + 0.03 = 0.06
        assert cost == 0.06

    def test_calculate_cost_anthropic_claude(
        self, anthropic_config: ModelConfig
    ) -> None:
        """Test cost calculation for Claude."""
        tokens = {"input": 2000, "output": 1000}

        cost = calculate_cost(tokens, anthropic_config)

        # Claude Opus pricing: input $0.015/1K, output $0.075/1K
        # Cost = (2000/1000)*0.015 + (1000/1000)*0.075 = 0.03 + 0.075 = 0.105
        assert cost == 0.105

    def test_calculate_cost_zero_tokens(self, openai_config: ModelConfig) -> None:
        """Test cost calculation with zero tokens."""
        tokens = {"input": 0, "output": 0}

        cost = calculate_cost(tokens, openai_config)

        assert cost == 0.0

    def test_calculate_cost_missing_input_tokens(
        self, openai_config: ModelConfig
    ) -> None:
        """Test cost when input tokens key is missing."""
        tokens = {"output": 1000}

        cost = calculate_cost(tokens, openai_config)

        # Input defaults to 0, only output cost
        # Cost = 0 + (1000/1000)*0.06 = 0.06
        assert cost == 0.06

    def test_calculate_cost_missing_output_tokens(
        self, openai_config: ModelConfig
    ) -> None:
        """Test cost when output tokens key is missing."""
        tokens = {"input": 1000}

        cost = calculate_cost(tokens, openai_config)

        # Output defaults to 0, only input cost
        assert cost == 0.03

    def test_calculate_cost_unknown_model(self) -> None:
        """Test cost calculation for unknown model."""
        config = ModelConfig(
            name="Unknown Model",
            provider="openai",
            model_id="unknown-model-v1",
        )
        tokens = {"input": 1000, "output": 500}

        cost = calculate_cost(tokens, config)

        assert cost == 0.0

    def test_calculate_cost_partial_model_match(self) -> None:
        """Test cost calculation with partial model ID matching."""
        # "gpt-4-0613" should match "gpt-4" pricing
        config = ModelConfig(
            name="GPT-4 Dated",
            provider="openai",
            model_id="gpt-4-0613",
        )
        tokens = {"input": 1000, "output": 500}

        cost = calculate_cost(tokens, config)

        # Should match gpt-4 pricing
        assert cost == 0.06

    def test_calculate_cost_all_models_have_pricing(self) -> None:
        """Test that all models in MODEL_PRICING can be calculated."""
        for model_id, pricing in MODEL_PRICING.items():
            config = ModelConfig(
                name=f"Test {model_id}",
                provider="openai",
                model_id=model_id,
            )
            tokens = {"input": 1000, "output": 500}

            cost = calculate_cost(tokens, config)

            assert cost >= 0
            assert "input" in pricing
            assert "output" in pricing

    def test_calculate_cost_rounding(self, openai_config: ModelConfig) -> None:
        """Test that cost is rounded to 6 decimal places."""
        tokens = {"input": 1, "output": 1}

        cost = calculate_cost(tokens, openai_config)

        # Very small cost, should still be rounded
        assert cost == 0.00009  # (1/1000)*0.03 + (1/1000)*0.06

    def test_calculate_cost_4o_mini(self) -> None:
        """Test cost calculation for GPT-4o-mini (cheapest model)."""
        config = ModelConfig(
            name="Cheap Model",
            provider="openai",
            model_id="gpt-4o-mini",
        )
        tokens = {"input": 1000000, "output": 500000}  # 1M input, 500K output

        cost = calculate_cost(tokens, config)

        # gpt-4o-mini: input $0.00015/1K, output $0.0006/1K
        # Cost = (1000000/1000)*0.00015 + (500000/1000)*0.0006
        # = 1000*0.00015 + 500*0.0006 = 0.15 + 0.3 = 0.45
        assert cost == 0.45


# =============================================================================
# Test extract_token_usage
# =============================================================================


class TestExtractTokenUsage:
    """Tests for extract_token_usage function."""

    def test_extract_openai_format(self) -> None:
        """Test extracting tokens from OpenAI response format."""
        response = {
            "id": "chatcmpl-123",
            "object": "chat.completion",
            "usage": {
                "prompt_tokens": 100,
                "completion_tokens": 50,
                "total_tokens": 150,
            },
        }

        result = extract_token_usage(response)

        assert result["input"] == 100
        assert result["output"] == 50
        assert result["total"] == 150

    def test_extract_anthropic_format(self) -> None:
        """Test extracting tokens from Anthropic response format."""
        response = {
            "id": "msg_01AbCdeFgHiJkLmN",
            "type": "message",
            "usage": {
                "input_tokens": 200,
                "output_tokens": 100,
            },
        }

        result = extract_token_usage(response)

        assert result["input"] == 200
        assert result["output"] == 100
        assert result["total"] == 300  # Calculated from input + output

    def test_extract_missing_usage_section(self) -> None:
        """Test extraction when usage section is missing."""
        response = {"id": "test-123"}

        result = extract_token_usage(response)

        assert result["input"] == 0
        assert result["output"] == 0
        assert result["total"] == 0

    def test_extract_empty_usage(self) -> None:
        """Test extraction when usage section is empty."""
        response = {"id": "test-123", "usage": {}}

        result = extract_token_usage(response)

        assert result["input"] == 0
        assert result["output"] == 0
        assert result["total"] == 0

    def test_extract_legacy_format(self) -> None:
        """Test extraction from legacy format with 'input'/'output' keys."""
        response = {
            "usage": {
                "input": 150,
                "output": 75,
                "total": 225,
            }
        }

        result = extract_token_usage(response)

        assert result["input"] == 150
        assert result["output"] == 75
        assert result["total"] == 225

    def test_extract_partial_openai_data(self) -> None:
        """Test extraction with partial OpenAI data."""
        response = {
            "usage": {
                "prompt_tokens": 100,
                # Missing completion_tokens
                "total_tokens": 150,
            }
        }

        result = extract_token_usage(response)

        assert result["input"] == 100
        assert result["output"] == 0  # Defaults to 0
        assert result["total"] == 150  # Uses provided total

    def test_extract_partial_anthropic_data(self) -> None:
        """Test extraction with partial Anthropic data."""
        response = {
            "usage": {
                "input_tokens": 200,
                # Missing output_tokens
            }
        }

        result = extract_token_usage(response)

        assert result["input"] == 200
        assert result["output"] == 0
        assert result["total"] == 200  # Calculated

    def test_extract_returns_integers(self) -> None:
        """Test that extracted values are integers."""
        response = {
            "usage": {
                "prompt_tokens": 100.5,  # Float in data
                "completion_tokens": 50.7,
                "total_tokens": 151.2,
            }
        }

        result = extract_token_usage(response)

        assert isinstance(result["input"], int)
        assert isinstance(result["output"], int)
        assert isinstance(result["total"], int)
        assert result["input"] == 100
        assert result["output"] == 50
        assert result["total"] == 151

    def test_extract_nested_in_response(self) -> None:
        """Test extraction when usage is deeply nested."""
        # Should only look at top-level usage
        response = {
            "choices": [
                {
                    "usage": {  # This should be ignored
                        "prompt_tokens": 999,
                        "completion_tokens": 888,
                    }
                }
            ],
            "usage": {
                "prompt_tokens": 100,
                "completion_tokens": 50,
            },
        }

        result = extract_token_usage(response)

        # Should use top-level usage
        assert result["input"] == 100
        assert result["output"] == 50

# =============================================================================
# Integration Tests
# =============================================================================


class TestMetricsIntegration:
    """Integration tests for metrics service."""

    def test_full_workflow_with_real_response(self) -> None:
        """Test a complete workflow: extract tokens, calculate metrics, calculate cost."""
        # Simulated API response
        api_response = {
            "id": "chatcmpl-test",
            "output": {
                "contract_number": "CNT-001",
                "party_name": "ABC Corp",
            },
            "usage": {
                "prompt_tokens": 2000,
                "completion_tokens": 500,
                "total_tokens": 2500,
            },
        }

        # Ground truth
        ground_truth = {
            "contract_number": "CNT-001",
            "party_name": "ABC Corp",
            "start_date": "2024-01-01",
        }

        # Extract tokens
        tokens = extract_token_usage(api_response)

        # Calculate metrics
        metrics = calculate_metrics(api_response["output"], ground_truth)

        # Calculate cost
        config = ModelConfig(
            name="Test",
            provider="openai",
            model_id="gpt-4",
        )
        cost = calculate_cost(tokens, config)

        # Verify
        assert tokens["input"] == 2000
        assert tokens["output"] == 500
        assert metrics["recall"] == approx(2 / 3)
        assert metrics["missing_fields"] == ["start_date"]
        assert cost > 0

    def test_different_provider_formats(self) -> None:
        """Test handling responses from different providers."""
        providers = [
            {
                "name": "OpenAI",
                "response": {
                    "usage": {
                        "prompt_tokens": 100,
                        "completion_tokens": 50,
                        "total_tokens": 150,
                    }
                },
                "expected_input": 100,
                "expected_output": 50,
            },
            {
                "name": "Anthropic",
                "response": {
                    "usage": {
                        "input_tokens": 200,
                        "output_tokens": 100,
                    }
                },
                "expected_input": 200,
                "expected_output": 100,
            },
        ]

        for provider in providers:
            result = extract_token_usage(provider["response"])
            assert result["input"] == provider["expected_input"], (
                f"Failed for {provider['name']}"
            )
            assert result["output"] == provider["expected_output"], (
                f"Failed for {provider['name']}"
            )

    def test_metrics_with_various_output_formats(self) -> None:
        """Test metrics calculation with different output formats."""
        ground_truth = {
            "string_field": "value",
            "number_field": 42,
            "boolean_field": True,
            "null_field": None,
            "array_field": [1, 2, 3],
            "object_field": {"nested": "value"},
        }

        # Test with all fields present
        output_complete = ground_truth.copy()
        result = calculate_metrics(output_complete, ground_truth)
        assert result["recall"] == 1.0

        # Test with some fields missing
        output_partial = {
            "string_field": "value",
            "number_field": 42,
        }
        result = calculate_metrics(output_partial, ground_truth)
        assert result["recall"] == approx(2 / 7)

    def test_cost_calculation_edge_cases(self) -> None:
        """Test cost calculation edge cases."""
        config = ModelConfig(
            name="Test",
            provider="openai",
            model_id="gpt-4",
        )

        # Very large token count
        tokens_large = {"input": 10000000, "output": 5000000}
        cost_large = calculate_cost(tokens_large, config)
        assert cost_large > 0
        assert cost_large == 600.0  # (10M/1K)*0.03 + (5M/1K)*0.06

        # Single token
        tokens_single = {"input": 1, "output": 1}
        cost_single = calculate_cost(tokens_single, config)
        assert cost_single > 0
