# Phase B3: Metrics Service Summary

**Phase:** B (Backend Core)  
**Plan:** B3 (Metrics Service)  
**Status:** ✅ COMPLETE  
**Completed:** 2026-02-11  
**Duration:** ~5 minutes

---

## Overview

Created a comprehensive metrics calculation service for evaluating prompt extraction quality. The service provides field-level comparison metrics (recall, precision, F1), cost estimation for API calls, and token usage extraction from provider responses.

## Deliverables

### Files Created

| File | Description | Lines |
|------|-------------|-------|
| `mvp/services/metrics.py` | Metrics calculation functions | ~235 |
| `mvp/services/__init__.py` | Package exports for metrics | ~10 |

### Functions Implemented

#### 1. `calculate_metrics(output: Dict, ground_truth: Dict) -> Dict`

Compares extracted output against ground truth and calculates quality metrics.

**Returns:**
- `recall: float` - Matched fields / total GT fields (0.0-1.0)
- `precision: float` - Matched fields / total output fields (0.0-1.0)
- `f1: float` - Harmonic mean: 2 * (precision * recall) / (precision + recall)
- `missing_fields: List[str]` - Fields present in GT but missing in output
- `extra_fields: List[str]` - Fields present in output but not in GT
- `total_gt_fields: int` - Total field count in ground truth
- `total_output_fields: int` - Total field count in output
- `matched_fields: int` - Number of matching fields

**Features:**
- Field-level comparison with case-insensitive matching
- Supports nested dictionary structures (e.g., `user.name`)
- Handles empty inputs gracefully

**Example:**
```python
output = {"name": "John", "age": 30}
ground_truth = {"name": "John", "age": 30, "email": "john@example.com"}
metrics = calculate_metrics(output, ground_truth)
# Result: recall=0.667, precision=1.0, f1=0.8, missing_fields=["email"]
```

#### 2. `calculate_cost(tokens: Dict, model_config: ModelConfig) -> float`

Estimates API call cost based on token usage and model pricing.

**Parameters:**
- `tokens: Dict` - Contains `input` and `output` token counts
- `model_config: ModelConfig` - Model configuration with model_id

**Returns:**
- `cost: float` - Estimated cost in USD

**Supported Models:**
- OpenAI: gpt-4, gpt-4-turbo, gpt-4o, gpt-4o-mini, gpt-3.5-turbo
- Anthropic: claude-3-opus, claude-3-sonnet, claude-3-haiku
- Legacy: text-davinci-003

**Features:**
- Partial model ID matching (e.g., "gpt-4-0613" matches "gpt-4" pricing)
- Returns 0.0 for unknown models (safe default)

**Example:**
```python
model = ModelConfig(name="Test", provider="openai", model_id="gpt-4")
tokens = {"input": 2000, "output": 1000}
cost = calculate_cost(tokens, model)  # Returns $0.12
```

#### 3. `extract_token_usage(response: Dict) -> Dict`

Extracts token counts from API responses, supporting multiple provider formats.

**Parameters:**
- `response: Dict` - API response dictionary

**Returns:**
- `input: int` - Input/prompt tokens
- `output: int` - Output/completion tokens
- `total: int` - Total tokens (input + output)

**Supported Formats:**
- OpenAI: `{usage: {prompt_tokens, completion_tokens, total_tokens}}`
- Anthropic: `{usage: {input_tokens, output_tokens}}`
- Legacy: Falls back to `{usage: {input, output, total}}`

**Example:**
```python
# OpenAI format
response = {"usage": {"prompt_tokens": 100, "completion_tokens": 50}}
tokens = extract_token_usage(response)
# Result: {"input": 100, "output": 50, "total": 150}
```

## Testing

All functions verified with comprehensive tests:

✅ **calculate_metrics**
- Basic field comparison (recall, precision, F1)
- Nested dictionary support (e.g., `user.email`)
- Empty ground truth handling
- Missing fields identification

✅ **calculate_cost**
- GPT-4 pricing calculation
- GPT-3.5 pricing calculation
- Unknown model handling (returns 0.0)
- Partial model ID matching

✅ **extract_token_usage**
- OpenAI response format
- Anthropic response format
- Token totals calculation

## Technical Details

### Key Features

1. **Field-level Metrics** - Compares individual fields, not just whole documents
2. **Nested Support** - Handles arbitrarily deep dictionary nesting
3. **Multi-provider** - Works with OpenAI and Anthropic APIs
4. **Pricing Table** - Centralized MODEL_PRICING dictionary for easy updates
5. **Safe Defaults** - Returns 0 for unknown models, handles edge cases

### Helper Functions

- `_normalize_field_name()` - Case-insensitive field comparison
- `_get_all_fields()` - Recursively extracts all field paths from nested dicts

### Design Decisions

1. **Field paths in dot notation** - `user.address.city` instead of nested access
2. **Case-insensitive matching** - "Name" matches "name" matches "NAME"
3. **Partial model matching** - Handles dated model IDs like "gpt-4-0613"
4. **Mutable MODEL_PRICING** - Can be updated at runtime for price changes

## Deviations from Plan

### Bug Fix: Nested Field Path Bug

**Found during:** Task 1 (calculate_metrics)  
**Issue:** Field paths for nested dictionaries showed double dots: `user..email`  
**Fix:** Corrected path construction logic in `_get_all_fields()`  
**Result:** Proper paths like `user.email` and `level1.level2.field`

## Dependencies

**Requires:**
- Phase B1 (Storage Service) - Directory structure
- Phase B2 (Data Models) - ModelConfig for cost calculation

**Provides for:**
- Phase C3 (Run Endpoints) - Metrics calculation for runs
- Phase F1 (Pipeline Integration) - Evaluation metrics
- Phase G1 (Test Framework) - Metrics verification

## Integration

The metrics service integrates with:

1. **ModelConfig (B2)** - Cost calculation uses model_id for pricing lookup
2. **Run model (B2)** - Run.metrics field populated by calculate_metrics()
3. **Run.tokens field** - Populated by extract_token_usage()
4. **Run.cost_usd field** - Populated by calculate_cost()

## Commits

| Hash | Message | Files |
|------|---------|-------|
| `[pending]` | feat(B3): create metrics calculation service | metrics.py |
| `[pending]` | feat(B3): export metrics functions from services package | __init__.py |
| `[pending]` | fix(B3): correct nested field path construction | metrics.py |

---

**SUMMARY:** Metrics service complete with field-level comparison, cost estimation, and token extraction. Ready for integration with run execution and pipeline evaluation.
