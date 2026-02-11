# Prompt Governor Architecture

This document describes the architecture of Prompt Governor, a lightweight prompt optimization tool for contract extraction.

## Table of Contents

- [System Overview](#system-overview)
- [Architecture Principles](#architecture-principles)
- [Backend Architecture](#backend-architecture)
- [Frontend Architecture](#frontend-architecture)
- [Data Flow](#data-flow)
- [Integration Points](#integration-points)
- [API Reference](#api-reference)

## System Overview

Prompt Governor is a web application for managing, testing, and optimizing LLM prompts for document extraction tasks. It provides:

- **Prompt Management:** Version control for prompts with branching/forking
- **Model Configuration:** Manage LLM provider settings and parameters
- **Document Processing:** Run extraction jobs against documents
- **Metrics Tracking:** Compare extraction results and track performance

### Tech Stack

| Layer | Technology |
|-------|------------|
| Backend | Python 3.13, FastAPI |
| Frontend | Vanilla JavaScript (ES6+), CSS3 |
| Data Storage | JSON files on filesystem |
| Containerization | Docker, Docker Compose |
| Validation | Pydantic v2 |

### High-Level Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                        Client Browser                        │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────┐ │
│  │  Prompts Tab    │  │  Configs Tab    │  │  Runs Tab   │ │
│  │  (JS + HTML)    │  │  (JS + HTML)    │  │ (JS + HTML) │ │
│  └────────┬────────┘  └────────┬────────┘  └──────┬──────┘ │
│           │                    │                   │        │
│           └────────────────────┼───────────────────┘        │
│                                │                            │
│                    ┌───────────┴───────────┐                │
│                    │   app.js (Core API)   │                │
│                    └───────────┬───────────┘                │
└────────────────────────────────┼────────────────────────────┘
                                 │ HTTP/JSON
                                 ▼
┌─────────────────────────────────────────────────────────────┐
│                      FastAPI Backend                         │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐          │
│  │   Prompts   │  │   Configs   │  │    Runs     │          │
│  │   Router    │  │   Router    │  │   Router    │          │
│  └──────┬──────┘  └──────┬──────┘  └──────┬──────┘          │
│         │                │                │                 │
│         └────────────────┼────────────────┘                 │
│                          │                                  │
│               ┌──────────┴──────────┐                       │
│               │  Pydantic Models    │                       │
│               └──────────┬──────────┘                       │
│                          │                                  │
│               ┌──────────┴──────────┐                       │
│               │  Storage Service    │                       │
│               └──────────┬──────────┘                       │
└──────────────────────────┼──────────────────────────────────┘
                           │ File I/O
                           ▼
┌─────────────────────────────────────────────────────────────┐
│                      Data Directory                          │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐          │
│  │  prompts/   │  │  configs/   │  │   runs/     │          │
│  │  (JSON)     │  │  (JSON)     │  │   (JSON)    │          │
│  └─────────────┘  └─────────────┘  └─────────────┘          │
└─────────────────────────────────────────────────────────────┘
```

## Architecture Principles

1. **Simplicity First:** No external databases, file-based storage for easy deployment
2. **Hot Reload:** Docker volumes for instant code changes during development
3. **Type Safety:** Pydantic models for validation and serialization
4. **Modular Design:** Clear separation between API, services, and models
5. **Zero Build Step:** Vanilla JS/CSS for frontend, no build pipeline needed

## Backend Architecture

### Directory Structure

```
backend/
├── mvp/
│   ├── __init__.py
│   ├── main.py                 # FastAPI application entry point
│   ├── api/
│   │   ├── __init__.py         # Router exports
│   │   ├── prompts.py          # Prompt management endpoints
│   │   ├── configs.py          # Model config endpoints
│   │   ├── runs.py             # Run execution endpoints
│   │   └── documents.py        # Document listing endpoints
│   ├── models/
│   │   ├── __init__.py         # Model exports
│   │   ├── prompt.py           # PromptVersion, PromptBlock
│   │   ├── config.py           # ModelConfig
│   │   ├── run.py              # Run
│   │   └── responses.py        # API response schemas
│   ├── services/
│   │   ├── __init__.py
│   │   ├── storage.py          # File-based JSON storage
│   │   ├── executor.py         # Run execution logic
│   │   └── metrics.py          # Metrics calculation
│   └── utils/
│       ├── __init__.py
│       └── errors.py           # Error handling utilities
```

### FastAPI Application Structure

```python
# mvp/main.py - Application entry point
app = FastAPI(
    title="Prompt Governor",
    description="Lightweight prompt optimization tool",
    version="0.1.0",
    lifespan=lifespan,  # Startup/shutdown events
)

# Middleware
app.add_middleware(CORSMiddleware, ...)

# Exception handlers
register_exception_handlers(app)

# API routes
app.include_router(api_router)  # All routes under /api

# Static files (frontend)
app.mount("/static", StaticFiles(...))
```

### Router Pattern

All API routers are centralized in `mvp/api/__init__.py`:

```python
api_router = APIRouter(prefix="/api")

api_router.include_router(prompts.router)   # /api/prompts
api_router.include_router(configs.router)   # /api/configs
api_router.include_router(runs.router)      # /api/runs
api_router.include_router(documents.router) # /api/documents
```

### Data Models

#### PromptVersion

Represents a version of a prompt with structured blocks:

```python
class PromptVersion(BaseModel):
    id: UUID                          # Auto-generated UUID
    name: str                         # Human-readable name
    description: Optional[str]        # Optional description
    blocks: List[PromptBlock]         # Structured content
    created_at: datetime              # Creation timestamp
    parent_id: Optional[UUID]         # For version branching
    tags: List[str]                   # Categorization tags
```

#### ModelConfig

Configuration for LLM providers:

```python
class ModelConfig(BaseModel):
    id: UUID
    name: str
    provider: str                     # openai, anthropic, openrouter
    model_id: str                     # e.g., "gpt-4", "claude-3-opus"
    reasoning_effort: Optional[str]   # low, medium, high
    temperature: float                # 0.0-2.0
    max_tokens: Optional[int]
    extra_params: dict                # Provider-specific params
    created_at: datetime
```

#### Run

Tracks an extraction execution:

```python
class Run(BaseModel):
    id: UUID
    prompt_id: UUID                   # Reference to prompt
    config_id: UUID                   # Reference to config
    document_name: str                # Document being processed
    status: str                       # pending/running/completed/failed
    started_at: datetime
    completed_at: Optional[datetime]
    output: Optional[dict]            # Extraction results
    metrics: Optional[dict]           # Performance metrics
    cost_usd: Optional[float]
    tokens: Optional[dict]            # {input, output}
```

### Storage Service

File-based JSON storage with the following structure:

```
data/
├── prompts/
│   ├── index.json                  # Metadata index
│   └── {uuid}.json                 # Individual prompts
├── configs/
│   ├── index.json
│   └── {uuid}.json
└── runs/
    ├── index.json
    └── {uuid}.json
```

Key functions:

```python
# mvp/services/storage.py
def load_json(filepath) -> dict: ...
def save_json(filepath, data) -> None: ...
def load_index(collection_name) -> dict: ...
def save_index(collection_name, data) -> None: ...
def generate_id() -> str: ...          # UUID v4 without dashes
```

### Error Handling

Centralized error handling with custom exceptions:

```python
# Custom exceptions
class NotFoundError(Exception): ...
class ValidationError(Exception): ...
class StorageError(Exception): ...
class PipelineError(Exception): ...

# Standardized error response
{
    "error": {
        "code": "not_found",
        "message": "Resource not found",
        "details": {...}
    }
}
```

## Frontend Architecture

### Directory Structure

```
static/
├── index.html              # Main HTML page with tab navigation
├── css/
│   └── style.css           # Comprehensive styles (30+ variables)
└── js/
    ├── app.js              # Core application (1078 lines)
    └── components/
        └── json-editor.js  # Reusable JSON editor component
```

### JavaScript Module Pattern

Uses IIFE (Immediately Invoked Function Expression) for encapsulation:

```javascript
(function() {
    'use strict';
    
    // ============================================
    // CONFIGURATION
    // ============================================
    const CONFIG = {
        API_BASE_URL: '/api',
        API_TIMEOUT: 30000,
        API_RETRIES: 3,
        // ...
    };
    
    // ============================================
    // STATE MANAGEMENT
    // ============================================
    const State = {
        currentTab: 'prompts',
        prompts: [],
        // ...
        
        set(key, value) { ... },
        get(key, defaultValue) { ... },
        on(key, callback) { ... },  // Subscribe to changes
    };
    
    // ============================================
    // API CLIENT
    // ============================================
    const API = {
        async get(url, options) { ... },
        async post(url, data, options) { ... },
        async put(url, data, options) { ... },
        async delete(url, options) { ... },
    };
    
    // ============================================
    // MODULE MANAGERS
    // ============================================
    const PromptManager = { ... };
    const ConfigManager = { ... };
    const RunManager = { ... };
    
    // Initialize on DOM ready
    document.addEventListener('DOMContentLoaded', init);
})();
```

### State Management

Simple observer pattern with localStorage persistence:

```javascript
const State = {
    // Data
    currentTab: 'prompts',
    prompts: [],
    configs: [],
    documents: [],
    runs: [],
    
    // Subscription system
    listeners: {},
    
    set(key, value) {
        const oldValue = this[key];
        this[key] = value;
        this.notify(key, value, oldValue);
        this._persist();  // Save to localStorage
    },
    
    on(key, callback) {
        // Subscribe to changes
        if (!this.listeners[key]) this.listeners[key] = [];
        this.listeners[key].push(callback);
        
        // Return unsubscribe function
        return () => { ... };
    }
};
```

### API Client

Robust HTTP client with retries and timeouts:

```javascript
const API = {
    async request(method, url, options = {}) {
        const controller = new AbortController();
        const timeoutId = setTimeout(() => controller.abort(), CONFIG.API_TIMEOUT);
        
        let lastError;
        for (let attempt = 0; attempt < CONFIG.API_RETRIES; attempt++) {
            try {
                const response = await fetch(url, {
                    method,
                    signal: controller.signal,
                    ...options
                });
                
                if (!response.ok) {
                    throw new APIError(response.status, await response.json());
                }
                
                return await response.json();
            } catch (error) {
                lastError = error;
                if (attempt < CONFIG.API_RETRIES - 1) {
                    await delay(CONFIG.API_RETRY_DELAY * (attempt + 1));
                }
            }
        }
        
        throw lastError;
    }
};
```

### UI Components

#### JSON Editor Component

Reusable component for JSON editing with validation:

```javascript
class JSONEditor {
    constructor(container, options = {}) {
        this.container = container;
        this.options = {
            readOnly: false,
            lineNumbers: true,
            height: '300px',
            ...options
        };
        this.value = '';
        this.isValid = true;
    }
    
    setValue(json) { ... }
    getValue() { ... }
    validate() { ... }
    format() { ... }
    compact() { ... }
}
```

Usage:

```javascript
const editor = new JSONEditor(container, {
    readOnly: false,
    lineNumbers: true
});
editor.setValue({ key: 'value' });
```

## Data Flow

### Prompt Creation Flow

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│  User fills │────▶│  Frontend   │────▶│   POST /api │
│    form     │     │  validates  │     │   /prompts  │
└─────────────┘     └─────────────┘     └──────┬──────┘
                                               │
                                               ▼
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│   Update    │◀────│   Update    │◀────│  Pydantic   │
│     UI      │     │   index     │     │  validates  │
└─────────────┘     └─────────────┘     └─────────────┘
                          │
                          ▼
                   ┌─────────────┐
                   │ Save JSON   │
                   │ to file     │
                   └─────────────┘
```

### Run Execution Flow

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│   Submit    │────▶│   POST      │────▶│  Validate   │
│    form     │     │  /api/runs  │     │  resources  │
└─────────────┘     └─────────────┘     └──────┬──────┘
                                               │
                                               ▼
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│   Return    │◀────│   Queue     │◀────│  Create     │
│   202 + ID  │     │   async     │     │  run.json   │
└─────────────┘     │   task      │     └─────────────┘
                    └──────┬──────┘
                           │
                           ▼
                    ┌─────────────┐
                    │ Background  │
                    │  executor   │
                    └─────────────┘
```

### Run Polling Flow

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│  Start      │────▶│  GET /api   │────▶│   Return    │
│  polling    │     │  /runs/{id} │     │   status    │
└─────────────┘     └─────────────┘     └─────────────┘
      │                                         │
      │ 2 seconds                               │ completed?
      │                                         │
      └─────────────────────────────────────────┘
                    No ◀────────────────────────┘
                    
                    Yes
                    ▼
            ┌─────────────┐
            │   Display   │
            │   results   │
            └─────────────┘
```

## Integration Points

### Document Processing

Documents are stored in `documents/` directory and processed by the executor service:

```python
# mvp/services/executor.py
async def execute_run(run_id, prompt_id, config_id, document_name):
    # 1. Load prompt and config
    prompt = await load_prompt(prompt_id)
    config = await load_config(config_id)
    
    # 2. Load document content
    document = await load_document(document_name)
    
    # 3. Call LLM with prompt + document
    result = await call_llm(prompt, config, document)
    
    # 4. Calculate metrics vs ground truth
    metrics = calculate_metrics(result, ground_truth)
    
    # 5. Update run with results
    await update_run(run_id, output=result, metrics=metrics)
```

### External LLM Providers

Currently supports:
- OpenAI (GPT-4, GPT-3.5)
- Anthropic (Claude 3)
- OpenRouter (unified API)

Configuration in `ModelConfig`:

```python
{
    "provider": "openai",
    "model_id": "gpt-4-turbo-preview",
    "temperature": 0.7,
    "max_tokens": 4096,
    "extra_params": {
        "top_p": 0.95
    }
}
```

### Ground Truth Comparison

Ground truth files stored in `ground_truth/`:

```
ground_truth/
└── {document_name}.json     # Expected extraction output
```

Metrics calculated:
- **Recall:** % of ground truth fields found
- **Precision:** % of extracted fields that match ground truth
- **F1 Score:** Harmonic mean of precision and recall
- **Latency:** Processing time in milliseconds
- **Cost:** USD spent on API call

## API Reference

### Endpoints Summary

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/health` | Health check |
| GET | `/api/prompts` | List all prompts |
| POST | `/api/prompts` | Create new prompt |
| GET | `/api/prompts/{id}` | Get prompt by ID |
| PUT | `/api/prompts/{id}` | Update prompt |
| DELETE | `/api/prompts/{id}` | Delete prompt |
| GET | `/api/prompts/{id}/diff/{other_id}` | Compare prompts |
| GET | `/api/configs` | List all configs |
| POST | `/api/configs` | Create new config |
| GET | `/api/configs/{id}` | Get config by ID |
| PUT | `/api/configs/{id}` | Update config |
| DELETE | `/api/configs/{id}` | Delete config |
| GET | `/api/runs` | List all runs |
| POST | `/api/runs` | Create and execute run |
| GET | `/api/runs/{id}` | Get run details |
| DELETE | `/api/runs/{id}` | Delete run |
| GET | `/api/runs/{id}/compare/{other_id}` | Compare runs |
| GET | `/api/documents` | List documents |
| GET | `/api/documents/{name}` | Get document info |

### Response Formats

#### Success Response

```json
{
    "data": { ... },
    "success": true
}
```

#### List Response

```json
{
    "data": [ ... ],
    "total": 42,
    "success": true,
    "pagination": {
        "page": 1,
        "per_page": 20,
        "total_pages": 3
    }
}
```

#### Error Response

```json
{
    "error": {
        "code": "validation_error",
        "message": "Invalid input data",
        "details": {
            "field": "temperature",
            "issue": "Must be between 0.0 and 2.0"
        }
    },
    "success": false
}
```

### Error Codes

| Code | HTTP Status | Description |
|------|-------------|-------------|
| `not_found` | 404 | Resource doesn't exist |
| `validation_error` | 422 | Invalid input data |
| `storage_error` | 500 | File system error |
| `pipeline_error` | 500 | Processing error |
| `bad_request` | 400 | Malformed request |

### Request/Response Examples

#### Create Prompt

Request:
```bash
curl -X POST http://localhost:8000/api/prompts \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Contract Extractor",
    "description": "Extract key contract fields",
    "blocks": [
      {
        "title": "System",
        "body": "Extract fields from contracts...",
        "comment": "Main instruction"
      }
    ],
    "tags": ["extraction", "contracts"]
  }'
```

Response:
```json
{
    "id": "550e8400e29b41d4a716446655440000",
    "name": "Contract Extractor",
    "description": "Extract key contract fields",
    "blocks": [...],
    "created_at": "2026-02-11T10:30:00Z",
    "parent_id": null,
    "tags": ["extraction", "contracts"]
}
```

#### Execute Run

Request:
```bash
curl -X POST http://localhost:8000/api/runs \
  -H "Content-Type: application/json" \
  -d '{
    "prompt_id": "550e8400e29b41d4a716446655440000",
    "config_id": "660f9511f30a52e5b827557766551111",
    "document_name": "contract_001.pdf"
  }'
```

Response (202 Accepted):
```json
{
    "run_id": "7710a622g41b63f6c938668877662222",
    "status": "pending",
    "message": "Run queued for execution"
}
```

---

For more details on specific endpoints, see the inline documentation in each router file or access the auto-generated docs at `http://localhost:8000/docs` when running the application.
