# Development Guide

Complete guide for setting up and developing Prompt Governor locally.

## Table of Contents

- [Prerequisites](#prerequisites)
- [Quick Start](#quick-start)
- [Development Setup](#development-setup)
- [Running Locally](#running-locally)
- [Project Structure](#project-structure)
- [Testing](#testing)
- [Debugging](#debugging)
- [Common Tasks](#common-tasks)
- [Troubleshooting](#troubleshooting)

## Prerequisites

### Required Software

| Tool | Version | Purpose |
|------|---------|---------|
| Docker | 24.0+ | Containerization |
| Docker Compose | 2.20+ | Multi-container orchestration |
| Git | 2.40+ | Version control |
| curl | any | HTTP requests for testing |

### Optional but Recommended

- **Python 3.13+** - For local development without Docker
- **VS Code** - With extensions:
  - Python
  - Pylance
  - Ruff (linting)
  - AutoDocstring

## Quick Start

Get the application running in 5 minutes:

```bash
# 1. Clone the repository
git clone <repository-url>
cd prompt_governor

# 2. Create required directories
mkdir -p data/{prompts,configs,runs} documents ground_truth cache

# 3. Set up environment
cp .env.example .env

# 4. Start the application
docker-compose up

# 5. Open in browser
open http://localhost:8000
```

## Development Setup

### 1. Environment Configuration

Create `.env` file:

```bash
cp .env.example .env
```

Edit `.env` with your API keys:

```bash
# Required for LLM integration
OPENAI_API_KEY=sk-...
ANTHROPIC_API_KEY=sk-ant-...
OPENROUTER_API_KEY=sk-or-...

# Optional: Override defaults
DOCUMENTS_PATH=/app/documents
DATA_PATH=/app/data
```

### 2. Directory Structure Setup

Create data directories:

```bash
# Data storage
mkdir -p data/prompts
mkdir -p data/configs
mkdir -p data/runs

# Documents to process
mkdir -p documents

# Ground truth for comparison
mkdir -p ground_truth

# Cache directory
mkdir -p cache
```

### 3. Add Sample Documents

Place PDF or text files in `documents/`:

```bash
# Example: Add a contract
cp ~/Downloads/contract_sample.pdf documents/

# Or create a test document
echo "Sample contract text..." > documents/test_contract.txt
```

### 4. Verify Setup

Check directory structure:

```bash
tree -L 2
```

Expected output:
```
.
├── Dockerfile
├── docker-compose.yml
├── requirements.mvp.txt
├── .env
├── data/
│   ├── prompts/
│   ├── configs/
│   └── runs/
├── documents/
├── ground_truth/
├── cache/
├── mvp/
│   ├── main.py
│   ├── api/
│   ├── models/
│   └── services/
└── static/
    ├── index.html
    ├── css/
    └── js/
```

## Running Locally

### Using Docker Compose (Recommended)

Start the application:

```bash
# Build and start
docker-compose up --build

# Run in background
docker-compose up -d

# View logs
docker-compose logs -f

# Stop
docker-compose down
```

The application will be available at:
- **Web UI:** http://localhost:8000
- **API Docs:** http://localhost:8000/docs
- **Health Check:** http://localhost:8000/api/health

### Local Python Development (Alternative)

For development without Docker:

```bash
# Create virtual environment
python3.13 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.mvp.txt

# Set environment
export PYTHONPATH=/path/to/prompt_governor
export DATA_PATH=./data
export DOCUMENTS_PATH=./documents

# Run application
uvicorn mvp.main:app --reload --host 0.0.0.0 --port 8000
```

### Hot Reload

Both Docker and local development support hot reload:

- **Backend changes:** Edit files in `mvp/`, server restarts automatically
- **Frontend changes:** Edit files in `static/`, refresh browser to see changes

### Volume Mounts

Docker Compose mounts these directories for development:

| Host Path | Container Path | Purpose |
|-----------|---------------|---------|
| `./mvp` | `/app/mvp` | Backend code (hot reload) |
| `./data` | `/app/data` | Data persistence |
| `./documents` | `/app/documents` | Input documents (read-only) |
| `./ground_truth` | `/app/ground_truth` | Expected outputs (read-only) |
| `./cache` | `/app/cache` | Cache directory |

## Project Structure

### Backend (`mvp/`)

```
mvp/
├── main.py                 # FastAPI entry point
├── api/                    # API route handlers
│   ├── __init__.py         # Router exports
│   ├── prompts.py          # Prompt CRUD + diff
│   ├── configs.py          # Model config CRUD
│   ├── runs.py             # Run execution
│   └── documents.py        # Document listing
├── models/                 # Pydantic data models
│   ├── prompt.py           # PromptVersion, PromptBlock
│   ├── config.py           # ModelConfig
│   ├── run.py              # Run
│   └── responses.py        # API response schemas
├── services/               # Business logic
│   ├── storage.py          # File-based JSON storage
│   ├── executor.py         # Run execution
│   └── metrics.py          # Metrics calculation
└── utils/
    └── errors.py           # Error handling
```

### Frontend (`static/`)

```
static/
├── index.html              # Main page with tab navigation
├── css/
│   └── style.css           # All styles (no preprocessor)
└── js/
    ├── app.js              # Core app (1078 lines)
    │   ├── State management
    │   ├── API client
    │   ├── PromptManager
    │   ├── ConfigManager
    │   └── RunManager
    └── components/
        └── json-editor.js  # Reusable JSON editor
```

## Testing

### Test Framework

We use **pytest** for testing. Install it:

```bash
pip install pytest pytest-asyncio pytest-cov
```

### Running Tests

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=mvp --cov-report=html

# Run specific test file
pytest tests/test_prompts.py

# Run specific test
pytest tests/test_prompts.py::test_create_prompt

# Run with verbose output
pytest -v

# Run only failed tests
pytest --lf
```

### Test Structure

Create `tests/` directory:

```bash
mkdir -p tests
```

Example test file (`tests/test_prompts.py`):

```python
import pytest
from fastapi.testclient import TestClient
from mvp.main import app

client = TestClient(app)


def test_list_prompts():
    """Test listing prompts returns empty list initially."""
    response = client.get("/api/prompts")
    assert response.status_code == 200
    data = response.json()
    assert "prompts" in data
    assert data["total"] == 0


def test_create_prompt():
    """Test creating a new prompt."""
    response = client.post(
        "/api/prompts",
        json={
            "name": "Test Prompt",
            "description": "A test prompt",
            "blocks": [{"title": "Block 1", "body": "Content"}],
            "tags": ["test"]
        }
    )
    assert response.status_code == 201
    data = response.json()
    assert data["name"] == "Test Prompt"
    assert "id" in data


def test_get_prompt():
    """Test getting a prompt by ID."""
    # First create a prompt
    create_response = client.post(
        "/api/prompts",
        json={"name": "Get Test", "blocks": []}
    )
    prompt_id = create_response.json()["id"]
    
    # Then get it
    response = client.get(f"/api/prompts/{prompt_id}")
    assert response.status_code == 200
    assert response.json()["id"] == prompt_id


def test_get_nonexistent_prompt():
    """Test getting a prompt that doesn't exist."""
    response = client.get("/api/prompts/nonexistent-id")
    assert response.status_code == 404
```

### Writing New Tests

#### Test Naming

- Use descriptive names: `test_<action>_<condition>_<expected_result>`
- Group related tests in classes

#### Test Patterns

```python
# Arrange-Act-Assert pattern
def test_example():
    # Arrange
    input_data = {"key": "value"}
    
    # Act
    result = process_data(input_data)
    
    # Assert
    assert result["success"] is True


# Parameterized tests
@pytest.mark.parametrize("input,expected", [
    ("valid", True),
    ("invalid", False),
    ("", False),
])
def test_validation(input, expected):
    assert validate_input(input) == expected


# Async tests
@pytest.mark.asyncio
async def test_async_function():
    result = await async_operation()
    assert result is not None
```

### Test Coverage

Current coverage targets:

| Module | Target |
|--------|--------|
| `mvp/api/` | 90% |
| `mvp/models/` | 95% |
| `mvp/services/` | 80% |
| `mvp/utils/` | 85% |

View coverage report:

```bash
pytest --cov=mvp --cov-report=html
open htmlcov/index.html
```

### Integration Tests

Test the full stack:

```python
def test_create_and_run():
    """Test creating a prompt, config, and running extraction."""
    # Create prompt
    prompt = client.post("/api/prompts", json={...}).json()
    
    # Create config
    config = client.post("/api/configs", json={...}).json()
    
    # Create run
    run = client.post("/api/runs", json={
        "prompt_id": prompt["id"],
        "config_id": config["id"],
        "document_name": "test.pdf"
    }).json()
    
    # Poll for completion
    for _ in range(10):
        status = client.get(f"/api/runs/{run['run_id']}").json()
        if status["status"] in ("completed", "failed"):
            break
        time.sleep(1)
    
    assert status["status"] == "completed"
```

## Debugging

### Backend Debugging

#### Using VS Code

Create `.vscode/launch.json`:

```json
{
    "version": "0.2.0",
    "configurations": [
        {
            "name": "Python: FastAPI",
            "type": "debugpy",
            "request": "launch",
            "module": "uvicorn",
            "args": [
                "mvp.main:app",
                "--reload",
                "--host", "0.0.0.0",
                "--port", "8000"
            ],
            "jinja": true,
            "justMyCode": false
        }
    ]
}
```

Press F5 to start debugging.

#### Using pdb

Insert breakpoints in code:

```python
def some_function():
    import pdb; pdb.set_trace()  # Breakpoint
    # ... code
```

Common pdb commands:
- `n` - Next line
- `s` - Step into
- `c` - Continue
- `p variable` - Print variable
- `q` - Quit

#### Logging

Use the configured logger:

```python
import logging
logger = logging.getLogger(__name__)

logger.info("Processing started")
logger.debug(f"Config: {config}")
logger.warning("Rate limit approaching")
logger.error("Failed to process", exc_info=True)
```

View logs:

```bash
# Docker logs
docker-compose logs -f prompt-governor

# With grep
docker-compose logs -f | grep ERROR
```

### Frontend Debugging

#### Browser DevTools

1. Open DevTools (F12 or Cmd+Option+I)
2. Go to Console tab for logs
3. Go to Network tab for API calls
4. Go to Sources tab for breakpoints

#### Console Logging

```javascript
// In app.js, add logging
console.log('State updated:', key, value);
console.error('API Error:', error);
console.table(data);  // Pretty print arrays/objects
```

#### Debug Mode

Add debug flag to CONFIG:

```javascript
const CONFIG = {
    // ... existing config
    DEBUG: true,
};

// Use in code
if (CONFIG.DEBUG) {
    console.log('Debug:', data);
}
```

#### Network Inspection

Monitor API calls in Network tab:

1. Open DevTools → Network
2. Filter by "Fetch/XHR"
3. Click on requests to see:
   - Request headers
   - Request payload
   - Response data
   - Status codes

### Docker Debugging

#### Enter Container

```bash
# Get shell access
docker-compose exec prompt-governor bash

# Check files
ls -la /app/data/prompts/
cat /app/data/prompts/index.json

# Check processes
ps aux
```

#### Check Volume Mounts

```bash
# Test endpoint
curl http://localhost:8000/api/test/volumes

# Expected output:
{
    "volumes_mounted": {
        "data": true,
        "documents": true,
        "ground_truth": true,
        "cache": true,
        "mvp": true
    },
    "all_mounted": true
}
```

## Common Tasks

### Adding a New API Endpoint

1. **Add route handler** in appropriate router file:

```python
# mvp/api/prompts.py

@router.get(
    "/{prompt_id}/export",
    response_model=PromptExportResponse,
    summary="Export prompt",
)
async def export_prompt(prompt_id: str) -> PromptExportResponse:
    """Export prompt in various formats."""
    prompt_data = _load_prompt(prompt_id)
    
    return PromptExportResponse(
        format="json",
        content=prompt_data,
        exported_at=datetime.utcnow()
    )
```

2. **Add response model** if needed:

```python
class PromptExportResponse(BaseModel):
    format: str
    content: dict
    exported_at: datetime
```

3. **Test the endpoint**:

```bash
curl http://localhost:8000/api/prompts/123/export
```

### Adding a New Frontend Tab

1. **Add tab button** in `index.html`:

```html
<li class="tab-item">
    <button class="tab-button" data-tab="analytics">
        <span class="tab-icon">📊</span>
        <span class="tab-label">Analytics</span>
    </button>
</li>
```

2. **Add tab content**:

```html
<section id="analytics" class="tab-content">
    <!-- Tab content -->
</section>
```

3. **Add styles** in `style.css`:

```css
#analytics .chart-container {
    /* Styles */
}
```

4. **Add JavaScript** in `app.js`:

```javascript
const AnalyticsManager = {
    init() {
        // Initialize
    },
    
    async loadData() {
        // Load analytics data
    }
};
```

### Database Migration (File-based)

Since we use file storage, "migrations" are manual:

1. **Backup data**:

```bash
cp -r data data.backup.$(date +%Y%m%d)
```

2. **Write migration script**:

```python
# scripts/migrate_v1_to_v2.py
import json
from pathlib import Path

def migrate_prompts():
    prompts_dir = Path("data/prompts")
    
    for file_path in prompts_dir.glob("*.json"):
        if file_path.name == "index.json":
            continue
            
        with open(file_path) as f:
            data = json.load(f)
        
        # Apply migration
        if "version" not in data:
            data["version"] = 2
            data["new_field"] = "default_value"
        
        with open(file_path, "w") as f:
            json.dump(data, f, indent=2)

if __name__ == "__main__":
    migrate_prompts()
```

3. **Run migration**:

```bash
python scripts/migrate_v1_to_v2.py
```

### Environment Variables

Available environment variables:

| Variable | Default | Description |
|----------|---------|-------------|
| `OPENAI_API_KEY` | - | OpenAI API key |
| `ANTHROPIC_API_KEY` | - | Anthropic API key |
| `OPENROUTER_API_KEY` | - | OpenRouter API key |
| `DOCUMENTS_PATH` | `/app/documents` | Documents directory |
| `DATA_PATH` | `/app/data` | Data directory |
| `LOG_LEVEL` | `INFO` | Logging level |

## Troubleshooting

### Common Issues

#### Port Already in Use

```bash
# Find process using port 8000
lsof -i :8000

# Kill process
kill -9 <PID>

# Or use different port
docker-compose up -d -p 8001:8000
```

#### Permission Denied on Data Directory

```bash
# Fix permissions
sudo chown -R $USER:$USER data/
chmod -R 755 data/
```

#### Module Not Found

```bash
# Rebuild container
docker-compose down
docker-compose up --build
```

#### Changes Not Reflected

```bash
# Restart container
docker-compose restart

# Or force rebuild
docker-compose down
docker-compose up --build --force-recreate
```

#### API Returns 500 Error

Check logs:

```bash
docker-compose logs -f --tail=100
```

Common causes:
- Missing data directories
- Invalid JSON in data files
- Missing environment variables

#### Frontend Not Loading

1. Check if static files are mounted:
   ```bash
   docker-compose exec prompt-governor ls -la /app/static/
   ```

2. Check browser console for errors

3. Hard refresh: Cmd+Shift+R (Mac) or Ctrl+Shift+R (Windows)

### Getting Help

1. Check [ARCHITECTURE.md](ARCHITECTURE.md) for system details
2. Check [CONTRIBUTING.md](CONTRIBUTING.md) for coding standards
3. Search existing issues
4. Create new issue with:
   - Error message
   - Steps to reproduce
   - Environment details (OS, Docker version)
   - Relevant logs

## Next Steps

After setup, explore:

1. **Create your first prompt:** Go to Prompts tab → New
2. **Configure a model:** Go to Model Configs tab → Add Config
3. **Run extraction:** Go to Run & Results tab → Select prompt, config, document → Run
4. **Compare results:** Run with different configs and compare

Happy developing!
