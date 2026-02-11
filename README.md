# Prompt Governor

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.13](https://img.shields.io/badge/python-3.13-blue.svg)](https://www.python.org/downloads/)
[![FastAPI](https://img.shields.io/badge/FastAPI-009688.svg?logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com/)
[![Docker](https://img.shields.io/badge/Docker-2496ED.svg?logo=docker&logoColor=white)](https://www.docker.com/)

> **Lightweight prompt optimization tool for contract extraction and structured data extraction workflows.**

Prompt Governor helps you manage, version, and optimize prompts for LLM-based data extraction. Track performance metrics, compare prompt versions, and iterate quickly to improve extraction accuracy.

---

## Table of Contents

- [Quick Start](#quick-start)
- [Architecture](#architecture)
- [Usage Guide](#usage-guide)
- [Configuration](#configuration)
- [Development Workflow](#development-workflow)
- [Troubleshooting](#troubleshooting)
- [API Reference](#api-reference)
- [License](#license)

---

## Quick Start

Get up and running in 5 minutes.

### Prerequisites

- **[Docker](https://docs.docker.com/get-docker/)** (v20.10+ recommended)
- **[Docker Compose](https://docs.docker.com/compose/install/)** (v2.0+ recommended)
- **API Keys** (at least one of):
  - [OpenAI API Key](https://platform.openai.com/api-keys)
  - [OpenRouter API Key](https://openrouter.ai/keys)

### Installation Steps

1. **Clone the repository** (if using git):
   ```bash
   git clone <repository-url>
   cd prompt-governor
   ```

2. **Set up environment variables**:
   ```bash
   cp .env.example .env
   ```
   
   Edit `.env` and add your API keys:
   ```bash
   OPENAI_API_KEY=sk-your-openai-api-key-here
   OPENROUTER_API_KEY=sk-or-v1-your-openrouter-api-key-here
   ```

3. **Create data directories** (optional - Docker will create these):
   ```bash
   mkdir -p data/prompts data/configs data/runs
   mkdir -p documents ground_truth cache
   ```

4. **Start the application**:
   ```bash
   docker-compose up -d
   ```

5. **Verify installation**:
   ```bash
   curl http://localhost:8000/api/health
   # Expected: {"status": "healthy", "version": "0.1.0"}
   ```

6. **Open the UI**:
   Navigate to [http://localhost:8000](http://localhost:8000) in your browser.

### First Run Instructions

> 📸 **[Screenshot Placeholder: Initial UI Load]**
> Shows the Prompt Governor interface with three tabs: Prompts, Model Configs, Run & Results

1. **Create your first model configuration**:
   - Click on the **"Model Configs"** tab
   - Click **"+ New Config"**
   - Select provider (OpenAI, Anthropic, or OpenRouter)
   - Enter model ID (e.g., `gpt-4-turbo`, `claude-3-opus`)
   - Adjust temperature (0.0 = deterministic, 1.0 = creative)
   - Click **"Save Configuration"**

2. **Create your first prompt**:
   - Click on the **"Prompts"** tab
   - Click **"+ New"**
   - Enter prompt name and description
   - Add prompt blocks with your extraction instructions
   - Click **"Save Version"**

3. **Run your first extraction**:
   - Place a document in the `./documents/` folder
   - Place corresponding ground truth in `./ground_truth/`
   - Click on **"Run & Results"** tab
   - Select your prompt, config, and document
   - Click **"Run Extraction"**

---

## Architecture

### System Diagram

```
┌─────────────────────────────────────────────────────────────┐
│                        Browser                              │
│                  (User Interface)                           │
└───────────────────────┬─────────────────────────────────────┘
                        │ HTTP
┌───────────────────────▼─────────────────────────────────────┐
│                    FastAPI Server                           │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐          │
│  │ /api/prompts│  │ /api/configs│  │  /api/runs  │          │
│  │    REST     │  │    REST     │  │    REST     │          │
│  └─────────────┘  └─────────────┘  └─────────────┘          │
└───────────────────────┬─────────────────────────────────────┘
                        │
        ┌───────────────┼───────────────┐
        │               │               │
┌───────▼──────┐ ┌──────▼──────┐ ┌─────▼──────┐
│  Storage     │ │  Documents  │ │ Ground     │
│  Service     │ │  Directory  │ │ Truth      │
│  (JSON)      │ │  (PDF/TXT)  │ │ (JSON)     │
└──────────────┘ └─────────────┘ └────────────┘
```

### Component Descriptions

#### Frontend (Browser)
- **Single Page Application** - Pure HTML/CSS/JavaScript, no build step required
- **Three main tabs**:
  - **Prompts**: Manage prompt versions with diff comparison
  - **Model Configs**: Configure AI model parameters
  - **Run & Results**: Execute extractions and view metrics
- **Real-time updates** via polling for run status
- **State persistence** using localStorage for user preferences

#### Backend (FastAPI)
- **FastAPI** - Modern, fast web framework for building APIs
- **Hot reload** - Automatic code reloading during development
- **Structured logging** - Comprehensive request/response logging
- **CORS enabled** - Frontend development support

#### Storage Layer
- **JSON-based storage** - Simple file-based persistence
- **Three collections**:
  - `data/prompts/` - Prompt versions
  - `data/configs/` - Model configurations  
  - `data/runs/` - Execution runs with results
- **Index files** - Fast lookups without loading all data
- **Atomic writes** - Safe concurrent access

#### Document Processing
- **Documents** - Source files (PDF, TXT) for extraction
- **Ground Truth** - Expected JSON output for comparison
- **Cache** - OCR results and API response caching

### Data Flow

```
User creates prompt ──┐
                      ▼
          ┌─────────────────────┐
          │  PromptVersion      │
          │  (stored in JSON)   │
          └──────────┬──────────┘
                     │
User creates config ─┤
                     ▼
          ┌─────────────────────┐
          │  ModelConfig        │
          │  (stored in JSON)   │
          └──────────┬──────────┘
                     │
User starts run ─────┤
                     ▼
          ┌─────────────────────┐
          │  Run                │
          │  (async execution)  │
          └──────────┬──────────┘
                     │
                     ▼
          ┌─────────────────────┐
          │  Document + Prompt  │
          │  ──────────────────▶│
          │  LLM API Call       │
          │  ◀───────────────── │
          │  Extracted Data     │
          └──────────┬──────────┘
                     │
                     ▼
          ┌─────────────────────┐
          │  Metrics Calculation│
          │  (vs Ground Truth)  │
          └──────────┬──────────┘
                     │
                     ▼
          ┌─────────────────────┐
          │  Results Display    │
          │  (Recall, Precision │
          │   F1, Cost, Tokens) │
          └─────────────────────┘
```

---

## Usage Guide

### How to Create/Edit Prompts

> 📸 **[Screenshot Placeholder: Prompts Tab - Creating a New Prompt]**
> Shows the Prompts tab with the editor open, demonstrating how to add prompt blocks

1. **Navigate to Prompts tab**

2. **To create a new prompt**:
   - Click **"+ New"** button
   - Enter:
     - **Name**: Descriptive name (e.g., "Contract Date Extractor")
     - **Description**: Purpose and notes
     - **Tags**: Comma-separated labels (e.g., "contracts, dates, v1")
   - In the JSON editor, add your prompt blocks:
     ```json
     {
       "name": "Contract Date Extractor",
       "description": "Extracts dates from contracts",
       "blocks": [
         {
           "title": "System Prompt",
           "body": "You are an expert at extracting dates from legal documents.",
           "comment": "Sets the context"
         },
         {
           "title": "Extraction Instructions",
           "body": "Extract all dates mentioned in the contract...",
           "comment": "Main extraction logic"
         }
       ],
       "tags": ["contracts", "dates"]
     }
     ```
   - Click **"Save Version"**

3. **To edit an existing prompt**:
   - Select prompt from the Version History sidebar
   - Make changes in the JSON editor
   - Click **"Save as New Version"** to create a new version
   - Or click **"Fork"** to create a child version

4. **Compare versions**:
   - Click **"Compare"** button
   - Select two versions in the modal
   - View differences highlighted (added/removed/modified)

> **Pro Tip**: Use tags to organize prompts by category. You can filter by tags using the dropdown in the filter bar.

### How to Create Model Configs

> 📸 **[Screenshot Placeholder: Model Configs Tab - Configuration Form]**
> Shows the model configuration form with provider selection and parameter inputs

1. **Navigate to Model Configs tab**

2. **Click "+ New Config"**

3. **Fill in the configuration**:
   - **Name**: Descriptive name (e.g., "GPT-4 Turbo - Balanced")
   - **Provider**: Choose from OpenAI, Anthropic, or OpenRouter
   - **Model ID**: 
     - OpenAI: `gpt-4-turbo`, `gpt-4o`, `gpt-3.5-turbo`
     - Anthropic: `claude-3-opus`, `claude-3-sonnet`
     - OpenRouter: Any model slug from openrouter.ai
   - **Reasoning Effort**: `minimal` | `medium` | `high` (OpenAI o-series models)
   - **Temperature**: 0.0 (deterministic) to 2.0 (creative)
   - **Max Tokens**: Maximum response length (optional)
   - **Extra Parameters**: JSON object for provider-specific settings

4. **Click "Save Configuration"**

> **Recommended Configurations**:
> - **High Accuracy**: Temperature 0.0, high reasoning effort
> - **Balanced**: Temperature 0.7, medium reasoning effort
> - **Creative**: Temperature 1.0+ for exploring variations

### How to Run Extractions

> 📸 **[Screenshot Placeholder: Run & Results Tab - During Execution]**
> Shows the run configuration form and progress bar while extraction is running

1. **Prepare your data**:
   ```bash
   # Place source document
   cp your-contract.pdf documents/
   
   # Place ground truth (expected output)
   echo '{"dates": ["2024-01-15", "2024-02-01"]}' > ground_truth/your-contract.json
   ```

2. **Navigate to Run & Results tab**

3. **Select configuration**:
   - **Prompt**: Choose your extraction prompt
   - **Configuration**: Choose your model config
   - **Document**: Select from available documents

4. **Click "Run Extraction"**

5. **Monitor progress**:
   - Progress bar shows execution status
   - Run appears in history with "running" status

6. **View results**:
   - Metrics display automatically when complete
   - JSON diff shows comparison with ground truth

### How to Compare Results

> 📸 **[Screenshot Placeholder: Results Comparison View]**
> Shows the diff viewer comparing extraction output with ground truth

1. **After a run completes**, results appear automatically in the Results panel

2. **Metrics displayed**:
   - **Recall**: Percentage of ground truth fields found
   - **Precision**: Percentage of extracted fields that are correct
   - **F1 Score**: Harmonic mean of recall and precision
   - **Cost**: API cost in USD
   - **Tokens**: Input/output token usage

3. **Compare with ground truth**:
   - Diff viewer shows side-by-side comparison
   - **Green**: Fields added (present in output, not in ground truth)
   - **Red**: Fields removed (present in ground truth, not in output)
   - **Yellow**: Fields modified (different values)

4. **Export results**:
   - Click **"Export JSON"** to download the full run data

### Interpreting Metrics

| Metric | Formula | Good Range | What It Means |
|--------|---------|------------|---------------|
| **Recall** | Found Fields ÷ Total Ground Truth | > 80% | How many expected fields were found |
| **Precision** | Correct Fields ÷ Total Extracted | > 80% | How many found fields are correct |
| **F1 Score** | 2 × (Recall × Precision) ÷ (Recall + Precision) | > 80% | Overall accuracy (balances recall & precision) |

> **Color Coding**:
> - 🟢 **Green border**: ≥ 80% (excellent)
> - 🟡 **Yellow border**: 60-79% (acceptable)
> - 🔴 **Red border**: < 60% (needs improvement)

**Missing Fields** are listed below metrics with specific field paths that weren't extracted.

---

## Configuration

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `OPENAI_API_KEY` | - | Your OpenAI API key |
| `OPENROUTER_API_KEY` | - | Your OpenRouter API key |
| `APP_HOST` | `0.0.0.0` | Host to bind the server |
| `APP_PORT` | `8000` | Port for the server |
| `LOG_LEVEL` | `INFO` | Logging verbosity (DEBUG, INFO, WARNING, ERROR) |
| `DATA_DIR` | `./data` | Base path for JSON storage |
| `DOCUMENTS_DIR` | `./documents` | Path for source documents |
| `GROUND_TRUTH_DIR` | `./ground_truth` | Path for ground truth files |
| `CACHE_DIR` | `./cache` | Path for cache files |
| `ENABLE_CACHE` | `true` | Enable API response caching |
| `TRACK_COSTS` | `true` | Track API costs |
| `API_TIMEOUT_SECONDS` | `120` | Max API call timeout |
| `API_MAX_RETRIES` | `3` | Retries for failed API calls |
| `RATE_LIMIT_PER_MINUTE` | `60` | API rate limit |

### API Keys Setup

**OpenAI**:
1. Go to [platform.openai.com/api-keys](https://platform.openai.com/api-keys)
2. Create new secret key
3. Copy to `.env`: `OPENAI_API_KEY=sk-...`

**OpenRouter**:
1. Go to [openrouter.ai/keys](https://openrouter.ai/keys)
2. Create new API key
3. Copy to `.env`: `OPENROUTER_API_KEY=sk-or-v1-...`

> **Security Note**: Never commit `.env` to git. It's already in `.gitignore`.

### Volume Mounts

The `docker-compose.yml` mounts several directories:

```yaml
volumes:
  # External codebase (read-only)
  - ~/Documents/projects/prompt_optimization:/app/prompt_optimization:ro
  
  # Data persistence
  - ./data:/app/data           # Prompts, configs, runs
  - ./documents:/app/documents:ro   # Source documents
  - ./ground_truth:/app/ground_truth:ro  # Expected outputs
  - ./cache:/app/cache         # OCR and API cache
  
  # Development
  - ./mvp:/app/mvp            # Hot reload for code changes
```

> **Note**: Directories with `:ro` are mounted read-only to prevent accidental modification.

---

## Development Workflow

### Hot Reload Usage

The development environment supports **hot reload**:

1. **Code changes** in `mvp/` are automatically detected
2. **Server restarts** automatically (usually within 1-2 seconds)
3. **Browser refresh** shows new changes

**Watching logs**:
```bash
docker-compose logs -f prompt-governor
```

### Adding New Features

**Adding a new API endpoint**:
1. Add route handler in appropriate `mvp/api/*.py` file
2. Include router in `mvp/api/__init__.py` if new file
3. Test with `curl` or browser at `http://localhost:8000/docs`

**Adding frontend features**:
1. Modify `static/index.html` for UI structure
2. Add styles to `static/css/style.css`
3. Add JavaScript to `static/js/app.js`
4. Refresh browser to see changes

**Adding new data models**:
1. Create model in `mvp/models/*.py`
2. Export from `mvp/models/__init__.py`
3. Server will auto-reload

### Running Tests

```bash
# Run all tests
docker-compose exec prompt-governor pytest

# Run with coverage
docker-compose exec prompt-governor pytest --cov=mvp

# Run specific test file
docker-compose exec prompt-governor pytest tests/test_prompts.py
```

### Useful Development Commands

```bash
# View container logs
docker-compose logs -f

# Restart the service
docker-compose restart prompt-governor

# Access container shell
docker-compose exec prompt-governor bash

# Check API health
curl http://localhost:8000/api/health

# Test volume mounts
curl http://localhost:8000/api/test/volumes

# View API documentation (Swagger UI)
open http://localhost:8000/docs

# View API documentation (ReDoc)
open http://localhost:8000/redoc
```

---

## Troubleshooting

### Common Issues

#### Issue: "Cannot connect to localhost:8000"

**Symptoms**: Browser shows "This site can't be reached"

**Solutions**:
1. Check if Docker is running:
   ```bash
   docker ps
   ```

2. Verify container is running:
   ```bash
   docker-compose ps
   ```

3. Check for port conflicts:
   ```bash
   lsof -i :8000
   ```
   If another service uses port 8000, change `APP_PORT` in `.env` and `docker-compose.yml`.

4. View container logs:
   ```bash
   docker-compose logs prompt-governor
   ```

#### Issue: "API Key Error" or "401 Unauthorized"

**Symptoms**: Extractions fail with authentication errors

**Solutions**:
1. Verify `.env` file exists:
   ```bash
   ls -la .env
   ```

2. Check API keys are set correctly:
   ```bash
   grep -E "(OPENAI|OPENROUTER)" .env
   ```

3. Restart container to load new env vars:
   ```bash
   docker-compose restart prompt-governor
   ```

4. Test API key directly:
   ```bash
   curl https://api.openai.com/v1/models \
     -H "Authorization: Bearer $OPENAI_API_KEY"
   ```

#### Issue: "Document not found" or "Ground truth not found"

**Symptoms**: Document doesn't appear in dropdown, or extraction fails

**Solutions**:
1. Verify file is in correct directory:
   ```bash
   ls -la documents/
   ls -la ground_truth/
   ```

2. Check file permissions:
   ```bash
   chmod 644 documents/*
   chmod 644 ground_truth/*
   ```

3. Verify volume mounts:
   ```bash
   curl http://localhost:8000/api/test/volumes
   ```
   All volumes should show `true`.

4. Check supported formats:
   - Documents: `.pdf`, `.txt`
   - Ground truth: `.json`

### Docker Issues

#### Container won't start

```bash
# Check for errors
docker-compose logs

# Rebuild the image
docker-compose build --no-cache

# Reset volumes (WARNING: deletes data)
docker-compose down -v
rm -rf data/* cache/*
docker-compose up -d
```

#### Permission denied errors

```bash
# Fix ownership on Linux/macOS
sudo chown -R $(id -u):$(id -g) data documents ground_truth cache

# Or adjust directory permissions
chmod -R 755 data documents ground_truth cache
```

#### Out of disk space

```bash
# Clean up Docker
docker system prune -a

# Remove unused volumes
docker volume prune
```

### API Errors

#### "422 Validation Error"

**Cause**: Invalid data format sent to API

**Solutions**:
- Check JSON syntax in prompt editor
- Verify temperature is between 0.0 and 2.0
- Ensure required fields are filled
- Check browser console for detailed error message

#### "500 Internal Server Error"

**Cause**: Server encountered unexpected error

**Solutions**:
1. Check server logs:
   ```bash
   docker-compose logs --tail=50 prompt-governor
   ```

2. Verify data directory structure:
   ```bash
   ls -la data/
   ls -la data/prompts/
   ls -la data/configs/
   ls -la data/runs/
   ```

3. Restart container:
   ```bash
   docker-compose restart prompt-governor
   ```

#### "Timeout Error"

**Cause**: API call took too long

**Solutions**:
- Increase timeout in `.env`: `API_TIMEOUT_SECONDS=180`
- Check your internet connection
- Verify API key is valid
- For large documents, consider chunking

---

## API Reference

### Available Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/health` | GET | Health check |
| `/api/prompts` | GET | List all prompts |
| `/api/prompts` | POST | Create new prompt |
| `/api/prompts/{id}` | GET | Get prompt by ID |
| `/api/prompts/{id}` | PUT | Update prompt |
| `/api/prompts/{id}` | DELETE | Delete prompt |
| `/api/prompts/{id}/diff/{other_id}` | GET | Compare two prompts |
| `/api/configs` | GET | List all configs |
| `/api/configs` | POST | Create new config |
| `/api/configs/{id}` | GET | Get config by ID |
| `/api/configs/{id}` | PUT | Update config |
| `/api/configs/{id}` | DELETE | Delete config |
| `/api/runs` | GET | List all runs |
| `/api/runs` | POST | Create and start run |
| `/api/runs/{id}` | GET | Get run details |
| `/api/runs/{id}` | DELETE | Delete run |
| `/api/runs/{id}/compare/{other_id}` | GET | Compare two runs |
| `/api/documents` | GET | List all documents |
| `/api/documents/{name}` | GET | Get document metadata |

### Interactive API Docs

- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

---

## License

MIT License - See LICENSE file for details.

---

## Contributing

Contributions are welcome! Please:

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests if applicable
5. Submit a pull request

---

## Support

- **Issues**: Open an issue on GitHub
- **Documentation**: See this README and inline code comments
- **API Docs**: http://localhost:8000/docs (when running)

---

## Screenshots & Demo

> 📸 **[Screenshot Placeholder: Main Dashboard]**
> Shows the main Prompt Governor interface with all three tabs visible

> 📸 **[Screenshot Placeholder: Prompt Editor with Version History]**
> Shows the split view with version list on left, editor on right

> 📸 **[Screenshot Placeholder: Model Config Form]**
> Shows the configuration form filled out with example values

> 📸 **[Screenshot Placeholder: Run Results with Metrics]**
> Shows completed run with recall, precision, F1 score cards

> 📸 **[Screenshot Placeholder: Diff Viewer]**
> Shows the JSON diff comparing output to ground truth

> 🎬 **[GIF Placeholder: Complete Workflow]**
> Animated GIF showing: create prompt → create config → run extraction → view results
