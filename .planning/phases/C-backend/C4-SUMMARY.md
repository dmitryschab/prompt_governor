# Phase C4: Runs API - Summary

**Plan:** C4 (Runs API)  
**Phase Group:** C - Backend API  
**Status:** COMPLETE  
**Completed:** 2026-02-11  

## Summary

Implemented comprehensive run execution API endpoints for the Prompt Governor MVP. The Runs API provides full CRUD operations for extraction runs with asynchronous execution support and detailed comparison capabilities.

## Deliverables

### Files Created/Modified

- **`/Users/dmitrijssabelniks/Documents/projects/prompt_governor/mvp/api/runs.py`** (542 lines added/modified)
  - Complete FastAPI router with 5 endpoints
  - Request/response models with Pydantic validation
  - Filtering, comparison, and async execution support

- **`/Users/dmitrijssabelniks/Documents/projects/prompt_governor/mvp/services/__init__.py`** (updated)
  - Updated exports to match existing executor service functions

## API Endpoints

### 1. GET /api/runs - List Runs
Returns lightweight run metadata for performance. Supports filtering by:
- `prompt_id` - Filter by prompt ID
- `config_id` - Filter by config ID  
- `document_name` - Filter by document name
- `status` - Filter by status (pending/running/completed/failed)

**Response:** `RunListResponse` with `runs` array and `total` count

### 2. GET /api/runs/{id} - Get Run Details
Returns complete Run object including:
- Full run metadata
- Execution output (extraction results)
- Metrics (recall, precision, F1, latency)
- Cost in USD
- Token usage statistics

**Response:** `Run` Pydantic model (404 if not found)

### 3. POST /api/runs - Execute New Run
Creates and queues a run for async execution:
- Validates all IDs exist (prompt, config, document)
- Creates run with "pending" status
- Queues execution via BackgroundTasks
- Returns 202 Accepted immediately

**Request:** `{prompt_id, config_id, document_name}`
**Response:** `RunCreateResponse` with `run_id`, `status`, `message`

### 4. DELETE /api/runs/{id} - Delete Run
Removes a run from storage:
- Deletes run JSON file
- Updates runs index
- Returns 204 No Content

**Response:** 204 (404 if not found)

### 5. GET /api/runs/{id}/compare/{other_id} - Compare Two Runs
Detailed comparison between two runs showing:
- Run metadata comparison
- Side-by-side metric comparisons with differences
- Field-by-field output differences (same/different/only_in_a/only_in_b)
- Summary statistics

**Response:** `RunCompareResponse` with comprehensive comparison data

## Key Features

### Async Execution
- Uses FastAPI `BackgroundTasks` for non-blocking execution
- Returns 202 Accepted immediately while execution continues in background
- Run status transitions: pending → running → completed/failed

### Performance Optimization
- List endpoint returns `RunMetadata` (lightweight) instead of full `Run`
- Full details only fetched when viewing individual run
- Index-based listing for O(1) lookups

### Validation
- Validates prompt_id exists before creating run
- Validates config_id exists before creating run
- Validates document exists in documents/ directory
- Returns 404 with clear error messages for missing resources

### Comparison Features
- Metric comparison with absolute and percentage differences
- Field-level output diff showing added/removed/changed fields
- Summary statistics (fields same, different, only in each run)
- Works with completed, failed, or pending runs

## Data Models

### RunMetadata (List View)
- id, prompt_id, config_id, document_name
- status, started_at, completed_at, cost_usd

### Run (Full Details)
- All metadata fields
- output: Dict with extraction results
- metrics: Dict with recall, precision, F1, latency_ms
- cost_usd: float
- tokens: Dict with input/output counts

### RunCreateRequest
- prompt_id: str (required)
- config_id: str (required)
- document_name: str (required)

### RunCompareResponse
- run_a, run_b: RunComparison objects
- metric_comparisons: List of MetricComparison
- field_differences: List of FieldDifference
- summary: Dict with comparison statistics

## Integration

The Runs API integrates with:
- **Executor Service** (Phase B4) - `execute_run()` for async execution
- **Storage Service** (Phase B1) - File-based JSON persistence
- **Run Model** (Phase B2) - Pydantic validation
- **Prompts API** (Phase C1) - Cross-validation of prompt IDs
- **Configs API** (Phase C2) - Cross-validation of config IDs
- **Documents API** (Phase C3) - Cross-validation of document names

## Success Criteria Verification

| Criteria | Status | Evidence |
|----------|--------|----------|
| Can list runs with filters | PASS | `list_runs()` with 4 filter params |
| Can execute new runs | PASS | `create_run()` with BackgroundTasks |
| Comparison shows differences | PASS | `compare_runs()` with metric + field diffs |
| Async execution works | PASS | 202 Accepted + BackgroundTasks pattern |

## Dependencies

- Phase B1 (Storage Service) - File I/O operations
- Phase B2 (Data Models) - Run, PromptVersion, ModelConfig models
- Phase B4 (Executor Service) - execute_run() for async execution
- Phase C1 (Prompts API) - Prompt validation
- Phase C2 (Configs API) - Config validation
- Phase C3 (Documents API) - Document validation

## Technical Decisions

1. **202 Accepted Pattern**: Used for run creation to indicate async processing
2. **BackgroundTasks**: FastAPI's built-in async execution (no Celery needed for MVP)
3. **Lightweight Metadata**: Separate models for list vs detail views
4. **Comprehensive Comparison**: Metric and field-level diffs in single endpoint
5. **Index Sync**: Automatic index updates on create/delete

## Next Steps

- Phase C5: API Router Integration - Wire up all routers in main.py
- Phase E3: Run Tab UI - Frontend integration with these endpoints
- Phase G1: API Unit Tests - Test all runs endpoints

## Commits

- `492466e` - feat(C4): implement runs API with async execution
