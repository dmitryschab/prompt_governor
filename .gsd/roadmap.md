# Prompt Governor - MVP Roadmap (Parallelizable)

## Overview
A lightweight, local prompt optimization application for reinsurance contract extraction.

**Goal:** Single-container FastAPI application with vanilla JS frontend for testing prompt variations against document extraction tasks. All data stored in JSON files on disk (no database).

**Est. Duration:** 3-4 days (with parallel execution)

---

## Phase Group A: Infrastructure (Parallel)

### Phase A1: Docker Setup
**Dependencies:** None

**Goal:** Create Docker container with FastAPI and all dependencies

**Tasks:**
- [ ] Create `Dockerfile` using Python 3.13-slim
- [ ] Install system dependencies (gcc)
- [ ] Copy requirements and install Python packages
- [ ] Expose port 8000

**Success Criteria:**
- [ ] Docker build succeeds
- [ ] Container can start

---

### Phase A2: Docker Compose Configuration
**Dependencies:** Phase A1

**Goal:** Configure docker-compose with volume mounts

**Tasks:**
- [ ] Create `docker-compose.yml`
- [ ] Configure volume mounts for:
  - Existing codebase (`prompt_optimization`)
  - Data persistence (`data/`)
  - Documents (`documents/`)
  - Ground truth (`ground_truth/`)
  - Cache (`cache/`)
  - Live reload (`mvp/`)
- [ ] Set environment variables
- [ ] Configure hot reload command

**Success Criteria:**
- [ ] `docker-compose up` starts successfully
- [ ] All volumes mounted correctly
- [ ] Hot reload works

---

### Phase A3: Directory Structure Setup
**Dependencies:** None

**Goal:** Create required directory structure

**Tasks:**
- [ ] Create `data/prompts/` - Prompt storage
- [ ] Create `data/configs/` - Config storage
- [ ] Create `data/runs/` - Run results storage
- [ ] Create `documents/` - Test documents
- [ ] Create `ground_truth/` - Ground truth JSONs
- [ ] Create `cache/` - OCR and intermediate files

**Success Criteria:**
- [ ] All directories exist
- [ ] Proper permissions set

---

### Phase A4: Requirements File
**Dependencies:** None

**Goal:** Define Python dependencies

**Tasks:**
- [ ] Create `requirements.mvp.txt`
- [ ] Add FastAPI >=0.100.0
- [ ] Add Uvicorn[standard] >=0.23.0
- [ ] Add python-multipart >=0.0.6
- [ ] Add aiofiles >=23.0.0
- [ ] Add pydantic >=2.0.0
- [ ] Add python-dotenv >=1.0.0

**Success Criteria:**
- [ ] All dependencies install without errors

---

### Phase A5: Environment Configuration
**Dependencies:** None

**Goal:** Set up environment variables and configuration

**Tasks:**
- [ ] Create `.env.example` with all required variables
- [ ] Document OPENAI_API_KEY usage
- [ ] Document OPENROUTER_API_KEY usage
- [ ] Create config loader utility

**Success Criteria:**
- [ ] Environment variables load correctly
- [ ] Sensible defaults provided

---

## Phase Group B: Backend Core (Parallel after A)

### Phase B1: Storage Service
**Dependencies:** Phase A3, Phase A4

**Goal:** Implement file-based JSON storage utilities

**Tasks:**
- [ ] Create `services/storage.py`
- [ ] Implement `load_json()` - read JSON file with error handling
- [ ] Implement `save_json()` - write JSON file with formatting
- [ ] Implement `list_files()` - list all files in directory
- [ ] Implement `generate_id()` - UUID generation
- [ ] Implement index management for prompts collection
- [ ] Implement index management for configs collection
- [ ] Implement index management for runs collection

**Success Criteria:**
- [ ] Can save and load JSON files
- [ ] Index files update correctly
- [ ] Error handling works for missing files

---

### Phase B2: Data Models
**Dependencies:** Phase B1

**Goal:** Define Pydantic models for all data types

**Tasks:**
- [ ] Create `models/prompt.py` - PromptVersion model
  - id, name, description, blocks, created_at, parent_id, tags
- [ ] Create `models/config.py` - ModelConfig model
  - id, name, provider, model_id, reasoning_effort, temperature, max_tokens, extra_params, created_at
- [ ] Create `models/run.py` - Run model
  - id, prompt_id, config_id, document_name, status, timestamps, output, metrics, cost_usd, tokens

**Success Criteria:**
- [ ] All models validate correctly
- [ ] JSON serialization/deserialization works

---

### Phase B3: Metrics Service
**Dependencies:** Phase B1, Phase B2

**Goal:** Implement metrics calculation wrapper

**Tasks:**
- [ ] Create `services/metrics.py`
- [ ] Import existing `calculate_recall_accuracy()` from utils
- [ ] Create wrapper function for metrics calculation
- [ ] Add cost calculation using OpenRouter client
- [ ] Add token usage extraction from responses
- [ ] Format metrics for storage

**Success Criteria:**
- [ ] Can calculate recall, precision, F1
- [ ] Cost calculation works
- [ ] Token usage tracked

---

### Phase B4: Executor Service
**Dependencies:** Phase B1, Phase B2, Phase B3

**Goal:** Implement run execution service

**Tasks:**
- [ ] Create `services/executor.py`
- [ ] Import `extract_modular_contract()` from pipeline
- [ ] Create function to load ground truth from file
- [ ] Create function to build model parameters from config
- [ ] Create function to execute extraction run
- [ ] Handle run status updates (pending, running, completed, failed)
- [ ] Save run results to storage

**Success Criteria:**
- [ ] Can execute extraction with prompt + config
- [ ] Ground truth loads correctly
- [ ] Run saved with all metadata

---

## Phase Group C: Backend API (Parallel after B)

### Phase C1: Prompt API
**Dependencies:** Phase B1, Phase B2

**Goal:** Implement prompt management endpoints

**Tasks:**
- [ ] Create `api/prompts.py`
- [ ] `GET /api/prompts` - List all prompts
- [ ] `GET /api/prompts/{id}` - Get prompt by ID
- [ ] `POST /api/prompts` - Create new prompt version
- [ ] `PUT /api/prompts/{id}` - Update prompt
- [ ] `DELETE /api/prompts/{id}` - Delete prompt
- [ ] `GET /api/prompts/{id}/diff/{other_id}` - Compare two versions

**Success Criteria:**
- [ ] All endpoints return correct JSON
- [ ] CRUD operations work
- [ ] Diff endpoint shows differences

---

### Phase C2: Config API
**Dependencies:** Phase B1, Phase B2

**Goal:** Implement model config endpoints

**Tasks:**
- [ ] Create `api/configs.py`
- [ ] `GET /api/configs` - List all configs
- [ ] `GET /api/configs/{id}` - Get config by ID
- [ ] `POST /api/configs` - Create config
- [ ] `PUT /api/configs/{id}` - Update config
- [ ] `DELETE /api/configs/{id}` - Delete config

**Success Criteria:**
- [ ] All endpoints return correct JSON
- [ ] CRUD operations work

---

### Phase C3: Documents API
**Dependencies:** Phase A3

**Goal:** Implement document listing endpoints

**Tasks:**
- [ ] Create `api/documents.py`
- [ ] `GET /api/documents` - List available documents
- [ ] `GET /api/documents/{name}` - Get document info (size, type)
- [ ] Support PDF and text files

**Success Criteria:**
- [ ] Lists files from documents directory
- [ ] Returns file metadata

---

### Phase C4: Runs API
**Dependencies:** Phase B4

**Goal:** Implement run execution endpoints

**Tasks:**
- [ ] Create `api/runs.py`
- [ ] `GET /api/runs` - List runs with filtering (prompt_id, config_id)
- [ ] `GET /api/runs/{id}` - Get run details
- [ ] `POST /api/runs` - Execute new run (async)
- [ ] `DELETE /api/runs/{id}` - Delete run
- [ ] `GET /api/runs/{id}/compare/{other_id}` - Compare two runs

**Success Criteria:**
- [ ] Can list runs with filters
- [ ] Can execute new runs
- [ ] Comparison shows differences

---

### Phase C5: API Router Integration
**Dependencies:** Phase C1, Phase C2, Phase C3, Phase C4

**Goal:** Wire up all API routes in FastAPI app

**Tasks:**
- [ ] Create `main.py` - FastAPI application entry
- [ ] Import all API routers
- [ ] Configure CORS for frontend
- [ ] Mount static files
- [ ] Add health check endpoint
- [ ] Add error handlers

**Success Criteria:**
- [ ] All endpoints accessible
- [ ] Static files served
- [ ] CORS configured for frontend

---

## Phase Group D: Frontend Core (Parallel after A)

### Phase D1: HTML Structure
**Dependencies:** None

**Goal:** Create base HTML page with tab navigation

**Tasks:**
- [ ] Create `static/index.html`
- [ ] Add header with app name
- [ ] Create tab navigation (Prompts, Configs, Run & Results)
- [ ] Create tab content containers
- [ ] Add footer with status

**Success Criteria:**
- [ ] Page loads correctly
- [ ] Tab structure visible

---

### Phase D2: CSS Styling
**Dependencies:** Phase D1

**Goal:** Create basic styling for the UI

**Tasks:**
- [ ] Create `static/css/style.css`
- [ ] Style tab navigation
- [ ] Style containers and layout
- [ ] Style forms and inputs
- [ ] Style buttons
- [ ] Add responsive design basics

**Success Criteria:**
- [ ] UI looks clean and professional
- [ ] Responsive on different screen sizes

---

### Phase D3: JavaScript Core
**Dependencies:** Phase D1

**Goal:** Create base JavaScript utilities

**Tasks:**
- [ ] Create `static/js/app.js`
- [ ] Implement tab switching logic
- [ ] Create API client functions (fetch wrapper)
- [ ] Create state management (simple store)
- [ ] Add error handling utilities
- [ ] Add loading state utilities

**Success Criteria:**
- [ ] Tabs switch correctly
- [ ] API client works
- [ ] State persists during session

---

### Phase D4: JSON Editor Component
**Dependencies:** Phase D3

**Goal:** Create reusable JSON editor component

**Tasks:**
- [ ] Create textarea with line numbers
- [ ] Add JSON validation
- [ ] Add syntax highlighting (optional)
- [ ] Add format/compact buttons
- [ ] Handle large JSON gracefully

**Success Criteria:**
- [ ] Can edit JSON with line numbers
- [ ] Validation shows errors
- [ ] Large files don't crash

---

## Phase Group E: Frontend Tabs (Parallel after D)

### Phase E1: Prompt Management Tab
**Dependencies:** Phase D3, Phase D4, Phase C1

**Goal:** Build prompt editor and version management

**Tasks:**
- [ ] Create dropdown for prompt selection
- [ ] Integrate JSON editor for prompt editing
- [ ] Add "Save as New Version" button
- [ ] Create version history sidebar
- [ ] Show parent/child relationships in history
- [ ] Create diff viewer component
- [ ] Add tag display and filtering

**Success Criteria:**
- [ ] Can select and edit prompts
- [ ] Can save new versions
- [ ] Version history shows correctly
- [ ] Can compare versions

---

### Phase E2: Model Config Tab
**Dependencies:** Phase D3, Phase C2

**Goal:** Build model configuration management UI

**Tasks:**
- [ ] Create config list view
- [ ] Create config creation form:
  - Provider dropdown (openai, anthropic, openrouter)
  - Model ID input
  - Reasoning effort dropdown (minimal, medium, high)
  - Temperature slider (0.0-1.0)
  - Max tokens input
  - Extra params JSON textarea
- [ ] Add edit/delete buttons
- [ ] Add form validation

**Success Criteria:**
- [ ] Can create new configs
- [ ] Can edit existing configs
- [ ] Form validation works

---

### Phase E3: Run & Results Tab
**Dependencies:** Phase D3, Phase C3, Phase C4

**Goal:** Build extraction runner and results viewer

**Tasks:**
- [ ] Create selection dropdowns:
  - Prompt selector (from saved prompts)
  - Config selector (from saved configs)
  - Document selector (from documents/)
- [ ] Add "Run Extraction" button
- [ ] Add loading/progress indicator
- [ ] Create results panel:
  - Large recall percentage display
  - Precision and F1 scores
  - Missing fields list
  - Side-by-side JSON diff (output vs ground truth)
  - Cost and token usage display
- [ ] Add run history list

**Success Criteria:**
- [ ] Can select all required inputs
- [ ] Run execution starts and shows progress
- [ ] Results display correctly
- [ ] JSON diff works

---

## Phase Group F: Integration (Parallel after B, C, E)

### Phase F1: Data Migration
**Dependencies:** Phase A3, Phase C1, Phase C3

**Goal:** Migrate existing data from prompt_optimization project

**Tasks:**
- [ ] Copy prompts from `prompt_optimization/prompt_templates/`
- [ ] Convert prompt format to new schema
- [ ] Copy documents from `prompt_optimization/docs/`
- [ ] Copy ground truth from `prompt_optimization/interpretations/`
- [ ] Create initial index files

**Success Criteria:**
- [ ] Existing prompts load in UI
- [ ] Documents appear in dropdown
- [ ] Ground truth files accessible

---

### Phase F2: Pipeline Integration
**Dependencies:** Phase B4, Phase F1

**Goal:** Integrate with existing extraction pipeline

**Tasks:**
- [ ] Import `schemas/contract.py` for validation
- [ ] Import `pipelines/modular_pipeline.py`
- [ ] Import `utils/recall_metrics.py`
- [ ] Import `utils/openrouter_client.py`
- [ ] Configure PYTHONPATH for imports
- [ ] Test pipeline execution end-to-end

**Success Criteria:**
- [ ] Pipeline imports work
- [ ] Can execute extraction with existing code
- [ ] Metrics calculate correctly

---

## Phase Group G: Testing (Parallel after F)

### Phase G1: API Unit Tests
**Dependencies:** Phase C5, Phase F2

**Goal:** Test all API endpoints

**Tasks:**
- [ ] Create test fixtures
- [ ] Test prompt CRUD endpoints
- [ ] Test config CRUD endpoints
- [ ] Test documents endpoints
- [ ] Test runs endpoints
- [ ] Test error handling

**Success Criteria:**
- [ ] All endpoints tested
- [ ] Tests pass

---

### Phase G2: Service Unit Tests
**Dependencies:** Phase B4

**Goal:** Test backend services

**Tasks:**
- [ ] Test storage service
- [ ] Test metrics service
- [ ] Test executor service
- [ ] Mock external dependencies

**Success Criteria:**
- [ ] All services tested
- [ ] Tests pass

---

### Phase G3: Integration Tests
**Dependencies:** Phase G1, Phase G2

**Goal:** Test full workflows

**Tasks:**
- [ ] Test complete workflow: create prompt → create config → run extraction
- [ ] Test error scenarios (missing files, invalid JSON)
- [ ] Test concurrent runs
- [ ] Test data persistence

**Success Criteria:**
- [ ] Full workflows tested
- [ ] Tests pass

---

### Phase G4: Frontend E2E Tests
**Dependencies:** Phase E3

**Goal:** Test frontend functionality

**Tasks:**
- [ ] Test tab navigation
- [ ] Test prompt CRUD operations
- [ ] Test config CRUD operations
- [ ] Test run execution flow
- [ ] Test error handling

**Success Criteria:**
- [ ] All frontend flows tested
- [ ] Tests pass

---

## Phase Group H: Polish (Parallel after E)

### Phase H1: Error Handling
**Dependencies:** Phase C5

**Goal:** Improve error handling across the app

**Tasks:**
- [ ] Add consistent error responses in API
- [ ] Add error display in frontend
- [ ] Handle network errors gracefully
- [ ] Add validation error messages
- [ ] Add retry logic for failed runs

**Success Criteria:**
- [ ] Errors display user-friendly messages
- [ ] No silent failures

---

### Phase H2: UI Polish
**Dependencies:** Phase E3

**Goal:** Improve UI/UX

**Tasks:**
- [ ] Add loading spinners
- [ ] Add success/error toast notifications
- [ ] Improve mobile responsiveness
- [ ] Add keyboard shortcuts
- [ ] Add dark mode (optional)

**Success Criteria:**
- [ ] UI feels polished and responsive
- [ ] Feedback is clear

---

### Phase H3: Performance Optimization
**Dependencies:** Phase E3

**Goal:** Optimize performance

**Tasks:**
- [ ] Add pagination for large lists
- [ ] Lazy load tab content
- [ ] Optimize JSON diff rendering
- [ ] Cache static assets
- [ ] Optimize bundle size

**Success Criteria:**
- [ ] App loads quickly
- [ ] Large JSON files don't freeze UI

---

## Phase Group I: Documentation (Parallel after F)

### Phase I1: Code Documentation
**Dependencies:** None

**Goal:** Add inline documentation

**Tasks:**
- [ ] Add docstrings to all functions
- [ ] Add type hints where missing
- [ ] Add comments for complex logic
- [ ] Update module docstrings

**Success Criteria:**
- [ ] Code is well-documented

---

### Phase I2: API Documentation
**Dependencies:** Phase C5

**Goal:** Document API endpoints

**Tasks:**
- [ ] Add OpenAPI/Swagger annotations
- [ ] Document request/response schemas
- [ ] Add example requests
- [ ] Document error responses

**Success Criteria:**
- [ ] Swagger UI available at /docs
- [ ] All endpoints documented

---

### Phase I3: User Documentation
**Dependencies:** Phase E3

**Goal:** Create user-facing documentation

**Tasks:**
- [ ] Update README.md with:
  - Quick start guide
  - Installation instructions
  - Configuration guide
  - Usage examples
- [ ] Add screenshots/GIFs
- [ ] Add troubleshooting guide

**Success Criteria:**
- [ ] New user can get started in 5 minutes
- [ ] README is comprehensive

---

### Phase I4: Development Documentation
**Dependencies:** Phase F2

**Goal:** Document development workflow

**Tasks:**
- [ ] Add development setup guide
- [ ] Document architecture decisions
- [ ] Add contribution guidelines
- [ ] Document testing procedures

**Success Criteria:**
- [ ] Developer docs are complete

---

## Phase Group J: Final (After all above)

### Phase J1: End-to-End Testing
**Dependencies:** Phase G3, Phase G4

**Goal:** Final validation

**Tasks:**
- [ ] Run full test suite
- [ ] Test on clean environment
- [ ] Verify hot reload works
- [ ] Verify data persistence
- [ ] Check for memory leaks

**Success Criteria:**
- [ ] All tests pass
- [ ] No critical bugs
- [ ] Ready for use

---

### Phase J2: Release Preparation
**Dependencies:** Phase J1

**Goal:** Prepare for release

**Tasks:**
- [ ] Tag version in git
- [ ] Create release notes
- [ ] Archive old data
- [ ] Clean up temporary files

**Success Criteria:**
- [ ] Release tagged
- [ ] Notes created

---

## Dependency Graph

```
Phase Group A (Infrastructure)
├── A1: Docker Setup
├── A2: Docker Compose (after A1)
├── A3: Directory Structure
├── A4: Requirements File
└── A5: Environment Config

Phase Group B (Backend Core) - after A
├── B1: Storage Service (after A3, A4)
├── B2: Data Models (after B1)
├── B3: Metrics Service (after B1, B2)
└── B4: Executor Service (after B1, B2, B3)

Phase Group C (Backend API) - after B
├── C1: Prompt API (after B1, B2)
├── C2: Config API (after B1, B2)
├── C3: Documents API (after A3)
├── C4: Runs API (after B4)
└── C5: API Router (after C1, C2, C3, C4)

Phase Group D (Frontend Core) - after A
├── D1: HTML Structure
├── D2: CSS Styling (after D1)
├── D3: JavaScript Core (after D1)
└── D4: JSON Editor (after D3)

Phase Group E (Frontend Tabs) - after D
├── E1: Prompt Tab (after D3, D4, C1)
├── E2: Config Tab (after D3, C2)
└── E3: Run Tab (after D3, C3, C4)

Phase Group F (Integration) - after B, C, E
├── F1: Data Migration (after A3, C1, C3)
└── F2: Pipeline Integration (after B4, F1)

Phase Group G (Testing) - after F
├── G1: API Tests (after C5, F2)
├── G2: Service Tests (after B4)
├── G3: Integration Tests (after G1, G2)
└── G4: Frontend E2E Tests (after E3)

Phase Group H (Polish) - after E
├── H1: Error Handling (after C5)
├── H2: UI Polish (after E3)
└── H3: Performance (after E3)

Phase Group I (Documentation) - after F
├── I1: Code Docs
├── I2: API Docs (after C5)
├── I3: User Docs (after E3)
└── I4: Dev Docs (after F2)

Phase Group J (Final)
├── J1: E2E Testing (after G3, G4)
└── J2: Release (after J1)
```

---

## Parallel Execution Strategy

**Week 1:**
- **Day 1-2:** Phase Group A (Infrastructure) - all in parallel
- **Day 2-3:** Phase Group B (Backend Core) - B1 first, then B2, B3, B4 in parallel
- **Day 3-4:** Phase Group C (Backend API) - C1, C2, C3, C4 in parallel, then C5
- **Day 3-4:** Phase Group D (Frontend Core) - D1, D2, D3, D4 in sequence

**Week 2:**
- **Day 1-2:** Phase Group E (Frontend Tabs) - E1, E2, E3 in parallel
- **Day 2-3:** Phase Group F (Integration) - F1, F2 in sequence
- **Day 3-4:** Phase Group G (Testing) - G1, G2, G3, G4 in parallel
- **Day 4:** Phase Group H (Polish) - H1, H2, H3 in parallel
- **Day 4-5:** Phase Group I (Documentation) - I1, I2, I3, I4 in parallel
- **Day 5:** Phase Group J (Final) - J1, J2 in sequence

---

## Size Estimates

| Phase | Est. Lines | Est. Hours |
|-------|-----------|-----------|
| A1-A5 | ~100 | 4 |
| B1-B4 | ~400 | 12 |
| C1-C5 | ~500 | 16 |
| D1-D4 | ~300 | 8 |
| E1-E3 | ~500 | 16 |
| F1-F2 | ~200 | 8 |
| G1-G4 | ~400 | 12 |
| H1-H3 | ~200 | 8 |
| I1-I4 | ~300 | 8 |
| J1-J2 | ~100 | 4 |
| **Total** | **~3000** | **~96** |

---

## Key Technical Decisions

1. **No database**: Filesystem is sufficient for local MVP
2. **No React build**: Vanilla JS loads faster, easier to modify
3. **Single container**: Simple deployment, easy to understand
4. **Volume mounts**: Reuse existing codebase without copying
5. **Hot reload**: Fast development iteration
6. **Parallel phases**: Maximize team velocity with independent work streams

---

## Future Enhancements (Post-MVP)

1. **Batch Runs**: Test multiple documents at once
2. **A/B Testing**: Compare prompt versions statistically
3. **Visual Diff**: Better JSON diff visualization
4. **Export**: PDF reports of results
5. **Git Integration**: Sync prompts with git
6. **User Auth**: Multi-user support
7. **Real Database**: PostgreSQL for scale
8. **WebSocket Updates**: Real-time run progress
9. **Prompt Templates**: Pre-built prompt starters
10. **Metrics Dashboard**: Charts and trends over time
