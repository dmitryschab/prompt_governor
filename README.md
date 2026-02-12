# Prompt Governor

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.13](https://img.shields.io/badge/python-3.13-blue.svg)](https://www.python.org/downloads/)
[![FastAPI](https://img.shields.io/badge/FastAPI-009688.svg?logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com/)

> **Lightweight prompt optimization tool for LLM-based data extraction.**

Manage, version, and optimize prompts. Track performance metrics (recall, precision, F1) and compare prompt versions against ground truth.

## Vibe

<img width="1441" height="774" alt="Screenshot 2026-02-12 at 18 30 03" src="https://github.com/user-attachments/assets/07d0d8a3-b95d-4a93-844b-5f835c18fe63" />

## Quick Start

```bash
# 1. Clone and setup
git clone https://github.com/dmitryschab/prompt_governor.git
cd prompt_governor

# 2. Add API keys to .env
cp .env.example .env
# Edit .env: OPENAI_API_KEY=sk-...

# 3. Start
docker-compose up -d

# 4. Open http://localhost:8000
```

## Tech Stack

- **Backend**: Python 3.13 + FastAPI + Pydantic
- **Frontend**: Vanilla HTML/CSS/JS (no build step)
- **Storage**: JSON files (no database)
- **LLMs**: OpenAI, OpenRouter support
- **Deploy**: Docker + Docker Compose

## Usage

1. **Create a Model Config** (Configs tab)
   - Select provider (OpenAI/OpenRouter)
   - Set model and temperature

2. **Create a Prompt** (Prompts tab)
   - Add prompt blocks with extraction instructions
   - Save versions and compare diffs

3. **Run Extraction** (Run & Results tab)
   - Place documents in `./documents/`
   - Place ground truth in `./ground_truth/`
   - Select prompt + config + document
   - View metrics (recall, precision, F1, cost)

## API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/health` | GET | Health check |
| `/api/prompts` | GET/POST | List/create prompts |
| `/api/prompts/{id}` | GET/PUT/DELETE | Prompt operations |
| `/api/configs` | GET/POST | List/create configs |
| `/api/runs` | GET/POST | List/create runs |
| `/api/runs/{id}` | GET/DELETE | Run operations |
| `/api/documents` | GET | List documents |

Interactive docs at `/docs` (Swagger UI) or `/redoc`.

## Environment Variables

```bash
OPENAI_API_KEY=sk-...
OPENROUTER_API_KEY=sk-or-v1-...
APP_PORT=8000
LOG_LEVEL=INFO
```

## License

MIT License - See LICENSE file for details.
