# Phase C1: Prompt API Summary

**Phase:** C (Backend API)  
**Plan:** C1 (Prompt API)  
**Status:** ✅ COMPLETE  
**Completed:** 2026-02-11  

---

## Overview

Implemented comprehensive REST API endpoints for managing prompt versions with full CRUD operations and advanced diff comparison. The API supports structured prompt content via PromptBlock model and maintains an index for efficient listing.

---

## Deliverables

### Files Created/Modified

| File | Description | Lines |
|------|-------------|-------|
| `mvp/api/prompts.py` | Prompt API router with 6 endpoints | 433 |
| `mvp/api/__init__.py` | Added prompts router export | +1 |
| `mvp/main.py` | Added prompts router registration | +1 |

### API Endpoints Implemented

| Method | Endpoint | Description | Status Codes |
|--------|----------|-------------|--------------|
| GET | `/api/prompts` | List all prompts with metadata, tag filtering | 200 |
| GET | `/api/prompts/{id}` | Get full prompt by ID | 200, 404 |
| POST | `/api/prompts` | Create new prompt version | 201, 422 |
| PUT | `/api/prompts/{id}` | Update existing prompt | 200, 404, 422 |
| DELETE | `/api/prompts/{id}` | Delete prompt | 204, 404 |
| GET | `/api/prompts/{id}/diff/{other_id}` | Compare two prompt versions | 200, 404 |

---

## Implementation Details

### Request/Response Models

**PromptCreateRequest:**
- `name` (required): Prompt name
- `description` (optional): Prompt description
- `blocks` (optional): List of PromptBlock objects with title, body, comment
- `parent_id` (optional): Parent version ID for versioning
- `tags` (optional): List of categorization tags

**PromptUpdateRequest:**
- All fields optional
- Only provided fields are updated
- Partial update support

**PromptMetadata (List Response):**
- Lightweight fields: id, name, description, created_at, parent_id, tags
- Sorted by created_at descending (newest first)
- Supports tag filtering with multiple tags

**PromptDiffResponse (Comparison):**
- `prompt_a_id`, `prompt_b_id`: IDs being compared
- `name_changed`, `description_changed`, `tags_changed`: Boolean flags
- `blocks_diff`: Detailed per-block differences (added/removed/modified)

**BlockDiff (Block-level diff):**
- `index`: Block position
- `status`: "added", "removed", or "modified"
- `old_block`, `new_block`: Block content for comparison

### Validation

- **UUID Generation:** Uses storage.generate_id() (32 hex chars without dashes)
- **Timestamp:** Auto-generated UTC timestamp on create (ISO format)
- **Block Structure:** Validates PromptBlock model with title, body, optional comment
- **Tag Filtering:** Case-insensitive tag matching (intersection logic)

### Storage Integration

- Uses existing storage service from Phase B1
- Each prompt saved as `{uuid}.json` in `data/prompts/`
- Index maintained at `data/prompts/index.json`
- Index stores lightweight PromptMetadata for efficient listing
- Index updated on create, update, and delete operations

### Diff Algorithm

The diff endpoint compares two prompts at multiple levels:

1. **Metadata Comparison:**
   - Name equality check
   - Description equality check  
   - Tags set comparison (case-sensitive)

2. **Block-level Diff:**
   - Position-by-position comparison
   - Tracks added blocks (in B but not A)
   - Tracks removed blocks (in A but not B)
   - Tracks modified blocks (same position, different content)
   - Returns full block content for both versions in diff

### Error Handling

- 404 Not Found: Prompt ID doesn't exist
- 422 Unprocessable Entity: Validation errors (invalid block structure)
- 500 Internal Server Error: File system errors

---

## Success Criteria Verification

✅ **All endpoints return correct JSON**
- Response models use Pydantic with proper serialization
- List endpoint returns PromptListResponse with PromptMetadata
- Single resource endpoints return full PromptVersion
- Diff endpoint returns PromptDiffResponse with BlockDiff array

✅ **CRUD operations work**
- Create: Generates UUID, sets timestamp, validates input, saves to storage, updates index
- Read: Loads from storage, returns full PromptVersion, 404 if not found
- Update: Loads existing, applies partial updates, validates, saves, updates index
- Delete: Removes file, updates index, returns 204

✅ **Diff endpoint shows differences**
- Compares names, descriptions, tags
- Block-by-block comparison with position tracking
- Returns detailed diff showing added/removed/modified blocks
- Full block content preserved for both versions

✅ **Tag filtering works**
- Multiple tag support (query parameter array)
- Case-insensitive matching
- Intersection logic (prompts matching ANY provided tag)

---

## Dependencies Satisfied

- ✅ Phase B1: Storage Service - Uses storage utilities (load_json, save_json, load_index, save_index)
- ✅ Phase B2: Data Models - Uses PromptVersion and PromptBlock Pydantic models

---

## Integration

The prompts router is registered in `mvp/main.py`:

```python
from mvp.api import configs, documents, prompts

app.include_router(configs.router)
app.include_router(documents.router)
app.include_router(prompts.router)
```

Routes are accessible under `/api/prompts/*` prefix.

---

## Technical Decisions

1. **Index Pattern:** Maintains separate lightweight index for O(n) list operations without loading full prompt content
2. **Partial Updates:** PUT with optional fields allows flexible updates without PATCH complexity
3. **Diff Granularity:** Block-level diff provides actionable comparison for prompt versions
4. **Timestamp Format:** ISO format with 'Z' suffix for UTC timezone clarity
5. **Tag Filtering:** Intersection-based filtering allows broad or specific searches

---

## Next Steps

Phase C1 is complete. This enables:
- Phase E1: Prompt Management Tab UI (can now call these endpoints)
- Phase E3: Run & Results (can reference prompts by ID)
- Phase F1: Data Migration (can migrate existing prompts via POST API)

---

## Commit

**Hash:** 6af7ab8  
**Message:** feat(C1): implement Prompt API endpoints
