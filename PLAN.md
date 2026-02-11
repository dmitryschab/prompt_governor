# Prompt Governor - MVP Specification

A lightweight, local prompt optimization application for reinsurance contract extraction.

## Overview

Single-container FastAPI application with vanilla JS frontend for testing prompt variations against document extraction tasks. All data stored in JSON files on disk (no database).

## Directory Structure

```
~/Documents/projects/prompt_governor/
├── data/
│   ├── prompts/              # Prompt template JSONs (versions)
│   ├── configs/              # Model configuration JSONs
│   └── runs/                 # Execution results with metrics
├── documents/                # PDF/text documents to test
├── ground_truth/             # Ground truth JSON files
└── cache/                    # OCR cache, intermediate files
```

## Tech Stack

**Single Container:**
- FastAPI (async web framework)
- Uvicorn (ASGI server)
- Vanilla JavaScript (no build step)
- Your existing Python codebase (mounted as volume)

**No Database** - Everything stored as JSON files in `data/` directory.

## Docker Setup

### docker-compose.yml

```yaml
version: '3.8'

services:
  prompt-governor:
    build: .
    ports:
      - "8000:8000"
    volumes:
      # Mount your existing project code
      - ~/Documents/projects/prompt_optimization:/app/prompt_optimization:ro
      # Mount data directory for persistence
      - ~/Documents/projects/prompt_governor/data:/app/data
      # Mount documents to test
      - ~/Documents/projects/prompt_governor/documents:/app/documents:ro
      # Mount ground truth
      - ~/Documents/projects/prompt_governor/ground_truth:/app/ground_truth:ro
      # Cache directory
      - ~/Documents/projects/prompt_governor/cache:/app/cache
      # Live reload for development
      - ./mvp:/app/mvp
    environment:
      - OPENAI_API_KEY=${OPENAI_API_KEY}
      - OPENROUTER_API_KEY=${OPENROUTER_API_KEY}
      - PYTHONPATH=/app
    command: uvicorn mvp.main:app --host 0.0.0.0 --port 8000 --reload
```

### Dockerfile

```dockerfile
FROM python:3.13-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install
COPY requirements.mvp.txt .
RUN pip install --no-cache-dir -r requirements.mvp.txt

# Copy MVP code
COPY mvp/ ./mvp/

# Expose port
EXPOSE 8000

# Run with hot reload for development
CMD ["uvicorn", "mvp.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]
```

### requirements.mvp.txt

```
fastapi>=0.100.0
uvicorn[standard]>=0.23.0
python-multipart>=0.0.6
aiofiles>=23.0.0
pydantic>=2.0.0
python-dotenv>=1.0.0
```

## Application Structure

```
mvp/
├── __init__.py
├── main.py                   # FastAPI application entry
├── api/
│   ├── __init__.py
│   ├── prompts.py           # Prompt CRUD endpoints
│   ├── configs.py           # Model config endpoints
│   ├── runs.py              # Execution endpoints
│   └── documents.py         # Document listing
├── services/
│   ├── __init__.py
│   ├── storage.py           # File-based storage utilities
│   ├── executor.py          # Run extraction using your pipeline
│   └── metrics.py           # Calculate metrics using your utils
├── static/
│   ├── index.html           # Main UI
│   ├── css/
│   │   └── style.css        # Basic styling
│   └── js/
│       └── app.js           # Vanilla JS frontend
└── templates/               # Optional: Jinja2 templates
```

## Data Models

### PromptVersion

```json
{
  "id": "uuid",
  "name": "FFH Contract Extraction v2.1",
  "description": "Improved currency detection",
  "blocks": [
    {"Title": "GOAL", "Body": "...", "Comment": "..."}
  ],
  "created_at": "2025-02-11T10:00:00Z",
  "parent_id": "uuid-or-null",
  "tags": ["production", "gpt-5-mini"]
}
```

### ModelConfig

```json
{
  "id": "uuid",
  "name": "GPT-5 Mini - Minimal",
  "provider": "openai",
  "model_id": "gpt-5-mini",
  "reasoning_effort": "minimal",
  "temperature": 0.0,
  "max_tokens": null,
  "extra_params": {},
  "created_at": "2025-02-11T10:00:00Z"
}
```

### Run

```json
{
  "id": "uuid",
  "prompt_id": "uuid",
  "config_id": "uuid",
  "document_name": "contract_001.pdf",
  "status": "completed",
  "started_at": "2025-02-11T10:00:00Z",
  "completed_at": "2025-02-11T10:00:45Z",
  "output": {...},
  "metrics": {
    "recall": 0.92,
    "precision": 0.89,
    "f1": 0.905,
    "missing_fields": ["/GeneralInformation/ContractName"],
    "total_gt_fields": 48,
    "matched_fields": 44
  },
  "cost_usd": 0.023,
  "tokens": {"input": 12000, "output": 3500}
}
```

## API Endpoints

### Prompts

```
GET    /api/prompts              → List all prompts
GET    /api/prompts/{id}         → Get prompt by ID
POST   /api/prompts              → Create new prompt version
PUT    /api/prompts/{id}         → Update prompt
DELETE /api/prompts/{id}         → Delete prompt
GET    /api/prompts/{id}/diff/{other_id} → Compare two versions
```

### Model Configs

```
GET    /api/configs              → List all configs
GET    /api/configs/{id}         → Get config by ID
POST   /api/configs              → Create config
PUT    /api/configs/{id}         → Update config
DELETE /api/configs/{id}         → Delete config
```

### Documents

```
GET    /api/documents            → List available documents
GET    /api/documents/{name}     → Get document info
```

### Runs

```
GET    /api/runs                 → List runs (filter by prompt/config)
GET    /api/runs/{id}            → Get run details
POST   /api/runs                 → Execute new run
DELETE /api/runs/{id}            → Delete run
GET    /api/runs/{id}/compare/{other_id} → Compare two runs
```

## Frontend UI

Single-page application with three tabs:

### Tab 1: Prompts
- Dropdown to select existing prompt
- JSON editor (textarea with line numbers)
- "Save as New Version" button
- Version history sidebar
- Diff viewer between versions

### Tab 2: Model Configs
- List of saved configs
- Form to create new config:
  - Provider (openai, anthropic, openrouter)
  - Model ID (gpt-5-mini, gpt-5, etc.)
  - Reasoning effort (minimal, medium, high)
  - Temperature slider
  - Extra params (JSON)

### Tab 3: Run & Results
- Select: Prompt (dropdown)
- Select: Model Config (dropdown)
- Select: Document (dropdown from documents/)
- "Run Extraction" button
- Results panel:
  - Recall percentage (big number)
  - Precision & F1
  - Missing fields list
  - Side-by-side JSON diff (output vs ground truth)
  - Cost and token usage

## Integration with Existing Code

The MVP reuses your existing:

1. **Prompt Templates** (`prompt_templates/`)
   - Load existing templates on startup
   - Save new versions to `data/prompts/`

2. **Pydantic Schemas** (`schemas/contract.py`)
   - Validate extracted output
   - Use schema for JSON diff

3. **Pipeline** (`pipelines/modular_pipeline.py`)
   - `extract_modular_contract()` - main extraction
   - Pass prompt blocks and model config

4. **Metrics** (`utils/recall_metrics.py`)
   - `calculate_recall_accuracy()` - compute metrics
   - Compare against ground truth

5. **OpenRouter Client** (`utils/openrouter_client.py`)
   - Use for cost estimation
   - Unified LLM interface

## Execution Flow

1. User selects prompt + config + document
2. Backend:
   - Load prompt blocks from JSON
   - Build model parameters
   - Call `extract_modular_contract()`
   - Load ground truth from `ground_truth/`
   - Calculate metrics using `calculate_recall_accuracy()`
   - Save run to `data/runs/{timestamp}_{id}.json`
3. Frontend displays results

## File Storage Structure

```
data/
├── prompts/
│   ├── prompt-001.json
│   ├── prompt-002.json
│   └── index.json              # Registry of all prompts
├── configs/
│   ├── config-001.json
│   └── index.json
└── runs/
    ├── 2025-02-11/
    │   ├── run-001.json
    │   └── run-002.json
    └── index.json              # Registry with filters
```

## Quick Start

1. **Setup directory:**
   ```bash
   mkdir -p ~/Documents/projects/prompt_governor/{data/{prompts,configs,runs},documents,ground_truth,cache}
   ```

2. **Copy existing prompts:**
   ```bash
   cp ~/Documents/projects/prompt_optimization/prompt_templates/* \
      ~/Documents/projects/prompt_governor/data/prompts/
   ```

3. **Copy sample documents:**
   ```bash
   cp ~/Documents/projects/prompt_optimization/docs/* \
      ~/Documents/projects/prompt_governor/documents/
   ```

4. **Copy ground truth:**
   ```bash
   cp ~/Documents/projects/prompt_optimization/interpretations/* \
      ~/Documents/projects/prompt_governor/ground_truth/
   ```

5. **Start the app:**
   ```bash
   cd ~/Documents/projects/prompt_governor
   docker-compose up
   ```

6. **Open browser:**
   http://localhost:8000

## Development Mode

With volume mounts:
- Edit `mvp/` files locally → auto-reload
- Edit prompts in UI → saved to `data/prompts/`
- Runs saved persistently
- No database to manage

## Future Enhancements (Post-MVP)

1. **Batch Runs**: Test multiple documents at once
2. **A/B Testing**: Compare prompt versions statistically
3. **Visual Diff**: Better JSON diff visualization
4. **Export**: PDF reports of results
5. **Git Integration**: Sync prompts with git
6. **User Auth**: Multi-user support
7. **Real Database**: PostgreSQL for scale

## Size Estimate

- **Backend code**: ~800 lines
- **Frontend code**: ~600 lines
- **Docker image**: ~150MB (Python slim)
- **Development time**: 3-4 days

## Key Decisions

1. **No database**: Filesystem is sufficient for local MVP
2. **No React build**: Vanilla JS loads faster, easier to modify
3. **Single container**: Simple deployment, easy to understand
4. **Volume mounts**: Reuse your existing codebase without copying
5. **Hot reload**: Fast development iteration
