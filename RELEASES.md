# Release Notes

## v0.1.0 - MVP Release (2026-02-11)

### Overview

Initial release of Prompt Governor - a lightweight prompt optimization tool for contract extraction and structured data extraction workflows.

### What's Included

This MVP release provides a complete end-to-end system for managing, versioning, and optimizing LLM prompts for data extraction tasks.

### Core Features

#### 1. Prompt Management
- **Version Control**: Create, edit, and version prompts with full history
- **Block-based Structure**: Organize prompts into logical blocks with titles, bodies, and comments
- **Diff Comparison**: Compare any two prompt versions side-by-side with visual highlighting
- **Tagging System**: Tag prompts for easy organization and filtering
- **Forking**: Create child versions from existing prompts

#### 2. Model Configuration
- **Multi-provider Support**: Configure OpenAI, Anthropic, and OpenRouter models
- **Parameter Control**: Set temperature, max tokens, and reasoning effort
- **Provider-specific Suggestions**: Auto-complete model IDs based on selected provider
- **JSON Extra Parameters**: Add provider-specific configuration options

#### 3. Extraction Runs
- **Async Execution**: Run extractions asynchronously with progress tracking
- **Performance Metrics**: Calculate recall, precision, and F1 scores
- **Ground Truth Comparison**: Compare extraction output against expected results
- **JSON Diff Viewer**: Visual diff highlighting for added/removed/modified fields
- **Cost Tracking**: Monitor API costs and token usage per run
- **Run History**: Browse and filter all past runs

#### 4. Document Management
- **Document Browser**: View and select from available documents
- **Ground Truth Support**: Link documents to expected JSON outputs
- **Format Support**: PDF and TXT document formats

#### 5. Web Interface
- **Three-tab Layout**: Prompts, Model Configs, and Run & Results
- **JSON Editor**: Syntax highlighting, validation, and formatting
- **Keyboard Shortcuts**: Alt+1/2/3 for tab switching, Ctrl+S to save
- **Responsive Design**: Works on desktop and mobile devices
- **Accessibility**: ARIA labels, keyboard navigation, screen reader support

#### 6. Performance Optimizations
- **Caching**: In-memory caching with TTL for all data types
- **Pagination**: Configurable pagination (50 items default, max 100)
- **Async I/O**: Non-blocking file operations
- **GZip Compression**: Automatic compression for responses >1KB
- **Virtual Scrolling**: Efficient rendering of large lists
- **Frontend Caching**: API response caching in browser

### Completed Phases

This release completes the following development phases:

#### Phase Group A: Infrastructure Bootstrap (4/4)
- ✅ A1: Docker Setup
- ✅ A2: Docker Compose Configuration
- ✅ A3: Directory Structure Setup
- ✅ A4: Requirements File

#### Phase Group B: Backend Core (2/4)
- ✅ B1: Storage Service
- ✅ B2: Data Models

#### Phase Group C: Backend API (5/5)
- ✅ C1: Prompts API
- ✅ C2: Configs API
- ✅ C3: Documents API
- ✅ C4: Runs API
- ✅ C5: Router Integration

#### Phase Group D: Frontend Core (4/4)
- ✅ D1: HTML Structure
- ✅ D2: CSS Styling
- ✅ D3: JavaScript Core
- ✅ D4: JSON Editor

#### Phase Group E: Frontend Tabs (3/3)
- ✅ E1: Prompt Management Tab
- ✅ E2: Model Config Tab
- ✅ E3: Run & Results Tab

#### Phase Group H: Polish (3/3)
- ✅ H1: Error Handling
- ✅ H2: UI Polish
- ✅ H3: Performance Optimization

#### Phase Group I: Documentation (4/4)
- ✅ I1: Code Documentation Setup
- ✅ I2: API Documentation
- ✅ I3: User Documentation
- ✅ I4: Development Documentation

### Technical Highlights

#### Backend
- **FastAPI**: Modern, fast web framework with automatic API docs
- **Pydantic v2**: Type-safe data validation and serialization
- **Structured Logging**: Comprehensive request/response logging
- **Error Handling**: Centralized error handling with custom exceptions
- **Background Tasks**: Async execution via FastAPI BackgroundTasks

#### Frontend
- **Vanilla JavaScript**: No build step required, pure ES6+
- **Component Architecture**: Reusable JSON editor and virtual scroller
- **State Management**: Client-side state with localStorage persistence
- **API Client**: Retry logic with exponential backoff and timeouts

#### Storage
- **JSON-based**: Simple file-based persistence
- **Atomic Writes**: Safe concurrent access
- **Index Files**: Fast lookups without loading all data

### API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/health` | GET | Health check |
| `/api/prompts` | GET, POST | List/create prompts |
| `/api/prompts/{id}` | GET, PUT, DELETE | Get/update/delete prompt |
| `/api/prompts/{id}/diff/{other_id}` | GET | Compare two prompts |
| `/api/configs` | GET, POST | List/create configs |
| `/api/configs/{id}` | GET, PUT, DELETE | Get/update/delete config |
| `/api/runs` | GET, POST | List/create runs |
| `/api/runs/{id}` | GET, DELETE | Get/delete run |
| `/api/runs/{id}/compare/{other_id}` | GET | Compare two runs |
| `/api/documents` | GET | List documents |
| `/api/documents/{name}` | GET | Get document metadata |
| `/api/performance/cache-stats` | GET | Cache statistics |

### Documentation

- **README.md**: Comprehensive user guide with quick start
- **ARCHITECTURE.md**: System architecture and data flow
- **DEVELOPMENT.md**: Developer setup and workflow guide
- **CONTRIBUTING.md**: Contribution guidelines
- **Interactive API Docs**: Swagger UI at `/docs`, ReDoc at `/redoc`

### Known Issues & Limitations

1. **Phase B3-B4 Incomplete**: Prompt Service and Config Service layers not fully implemented (API layer handles most functionality)
2. **Phase F-G Skipped**: Integration and Testing phases deferred to post-MVP
3. **No Authentication**: MVP assumes single-user local development
4. **No Persistent Database**: File-based storage only
5. **Single Language**: UI is English only
6. **Limited OCR**: No built-in OCR (expects pre-processed text/PDFs)
7. **No Multi-user Support**: Concurrent modifications may cause conflicts
8. **No Automated Testing**: Test suite not included in MVP

### System Requirements

- **Docker**: v20.10+ recommended
- **Docker Compose**: v2.0+ recommended
- **Memory**: 512MB RAM minimum
- **Disk**: 1GB free space
- **Browser**: Modern browser with ES6+ support

### Quick Start

```bash
# Clone and setup
cp .env.example .env
# Edit .env with your API keys

# Start the application
docker-compose up -d

# Verify installation
curl http://localhost:8000/api/health

# Open UI
open http://localhost:8000
```

See README.md for complete setup and usage instructions.

### Version Information

- **Version**: 0.1.0
- **Release Date**: 2026-02-11
- **Git Tag**: v0.1.0
- **Python**: 3.13
- **FastAPI**: 0.115+

### Credits

Built with:
- FastAPI - Web framework
- Pydantic - Data validation
- Uvicorn - ASGI server
- Docker - Containerization

### License

MIT License - See LICENSE file for details.

### Support

- **Issues**: Open an issue on GitHub
- **Documentation**: See README.md and inline code comments
- **API Docs**: http://localhost:8000/docs (when running)

---

## Future Releases

### v0.2.0 (Planned)
- User authentication and multi-user support
- Database backend (PostgreSQL)
- Automated test suite
- CI/CD pipeline
- Production deployment guide

### v0.3.0 (Planned)
- Advanced analytics and reporting
- Batch processing
- Import/export functionality
- Plugin system
- Multi-language support

---

*Release prepared by Claude - Get Shit Done Framework*
