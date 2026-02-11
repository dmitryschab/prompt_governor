# Contributing to Prompt Governor

Thank you for your interest in contributing to Prompt Governor! This document provides guidelines and standards for contributing to the project.

## Table of Contents

- [Development Setup](#development-setup)
- [Code Style Guide](#code-style-guide)
- [Commit Message Conventions](#commit-message-conventions)
- [Branch Naming](#branch-naming)
- [Pull Request Process](#pull-request-process)
- [Review Guidelines](#review-guidelines)

## Development Setup

1. **Clone the repository:**
   ```bash
   git clone <repository-url>
   cd prompt_governor
   ```

2. **Create data directories:**
   ```bash
   mkdir -p data/{prompts,configs,runs} documents ground_truth cache
   ```

3. **Set up environment:**
   ```bash
   cp .env.example .env
   # Edit .env with your API keys
   ```

4. **Start the development server:**
   ```bash
   docker-compose up
   ```

See [DEVELOPMENT.md](DEVELOPMENT.md) for detailed setup instructions.

## Code Style Guide

### Python

We follow PEP 8 with some project-specific conventions:

#### General Rules

- **Line length:** 100 characters maximum
- **Indentation:** 4 spaces (no tabs)
- **Quotes:** Double quotes for strings, single quotes only for nested quotes
- **Imports:** Grouped in order: stdlib, third-party, local

#### Import Organization

```python
# 1. Standard library imports
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

# 2. Third-party imports
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

# 3. Local imports
from mvp.models.prompt import PromptVersion
from mvp.services.storage import load_json
```

#### Naming Conventions

| Type | Convention | Example |
|------|------------|---------|
| Modules | `snake_case` | `storage.py`, `prompt_manager.py` |
| Classes | `PascalCase` | `PromptVersion`, `ModelConfig` |
| Functions | `snake_case` | `load_prompt()`, `create_run()` |
| Constants | `UPPER_SNAKE_CASE` | `MAX_RETRIES`, `API_TIMEOUT` |
| Private | `_leading_underscore` | `_validate_input()`, `_internal_helper()` |
| Type Variables | `PascalCase` or `T` | `T`, `ResponseType` |

#### Type Hints

Always use type hints for function signatures:

```python
def calculate_metrics(output: Dict[str, Any], ground_truth: Dict[str, Any]) -> Dict[str, float]:
    """Calculate precision, recall, and F1 score."""
    ...

async def get_prompt(prompt_id: str) -> PromptVersion:
    """Retrieve a prompt by ID."""
    ...
```

Use `Optional` for nullable values:

```python
from typing import Optional

def find_config(name: str) -> Optional[ModelConfig]:
    """Find config by name, returns None if not found."""
    ...
```

#### Docstrings

Use Google-style docstrings:

```python
def process_document(document_name: str, prompt_id: str) -> Run:
    """Process a document with the specified prompt.

    Args:
        document_name: Name of the document file in documents/
        prompt_id: UUID of the prompt version to use

    Returns:
        Run object with status, output, and metrics

    Raises:
        NotFoundError: If document or prompt doesn't exist
        ValidationError: If prompt_id is invalid
    """
    ...
```

#### Function Length

- Keep functions under 50 lines when possible
- Break complex logic into helper functions
- One level of abstraction per function

### JavaScript

#### General Rules

- **Line length:** 100 characters maximum
- **Indentation:** 4 spaces (no tabs)
- **Semicolons:** Required
- **Quotes:** Single quotes for strings, template literals for interpolation

#### Naming Conventions

| Type | Convention | Example |
|------|------------|---------|
| Variables | `camelCase` | `currentRun`, `apiClient` |
| Constants | `UPPER_SNAKE_CASE` | `API_TIMEOUT`, `MAX_RETRIES` |
| Functions | `camelCase` | `loadPrompts()`, `handleSubmit()` |
| Classes | `PascalCase` | `JSONEditor`, `PromptManager` |
| Private | `_leadingUnderscore` | `_validateInput()`, `_cache` |
| DOM Elements | Descriptive nouns | `promptList`, `submitButton` |

#### Module Pattern

Use IIFE (Immediately Invoked Function Expression) for encapsulation:

```javascript
(function() {
    'use strict';
    
    // Private variables
    const _cache = new Map();
    
    // Public API
    const MyModule = {
        init() {
            // Initialize module
        },
        
        async loadData() {
            // Load data
        }
    };
    
    // Expose to global scope
    window.MyModule = MyModule;
})();
```

#### JSDoc Comments

Document public methods:

```javascript
/**
 * Load prompt by ID and display in editor
 * @param {string} promptId - The prompt UUID
 * @returns {Promise<PromptVersion>} The loaded prompt
 * @throws {APIError} If prompt not found
 */
async function loadPrompt(promptId) {
    // Implementation
}
```

#### Async/Await

Prefer async/await over callbacks or raw promises:

```javascript
// Good
async function fetchData() {
    try {
        const response = await api.get('/data');
        return response.data;
    } catch (error) {
        console.error('Failed to fetch:', error);
        throw error;
    }
}

// Avoid
function fetchData() {
    return api.get('/data')
        .then(response => response.data)
        .catch(error => {
            console.error('Failed to fetch:', error);
            throw error;
        });
}
```

### CSS

#### General Rules

- **Indentation:** 4 spaces
- **Naming:** BEM-like naming for classes
- **Properties:** One per line, alphabetical order (within groups)

#### Naming Convention

```css
/* Block */
.prompt-card { }

/* Element */
.prompt-card__header { }
.prompt-card__title { }

/* Modifier */
.prompt-card--selected { }
.prompt-card--disabled { }
```

#### CSS Variables

Use CSS custom properties for theming:

```css
:root {
    --color-primary: #3b82f6;
    --color-error: #ef4444;
    --spacing-md: 1rem;
}

.button-primary {
    background-color: var(--color-primary);
    padding: var(--spacing-md);
}
```

## Commit Message Conventions

We follow [Conventional Commits](https://www.conventionalcommits.org/) specification.

### Format

```
<type>(<scope>): <subject>

<body>

<footer>
```

### Types

| Type | Description |
|------|-------------|
| `feat` | New feature |
| `fix` | Bug fix |
| `docs` | Documentation changes |
| `style` | Code style changes (formatting, no logic change) |
| `refactor` | Code refactoring |
| `perf` | Performance improvements |
| `test` | Adding or updating tests |
| `chore` | Build process, dependencies, tooling |

### Scopes

Common scopes for this project:

- `api` - API endpoints
- `models` - Data models
- `services` - Business logic services
- `ui` - Frontend UI components
- `storage` - File storage utilities
- `tests` - Test files
- `docs` - Documentation

### Examples

```
feat(api): add endpoint for comparing runs

Implements GET /api/runs/{id}/compare/{other_id} endpoint
that returns detailed metric and field comparisons.

Closes #123
```

```
fix(models): validate temperature range in ModelConfig

Temperature must be between 0.0 and 2.0. Added field_validator
to enforce this constraint.
```

```
docs: update API documentation for runs endpoints

Added request/response examples and error codes.
```

### Subject Guidelines

- Use imperative mood ("add" not "added" or "adds")
- Don't capitalize first letter
- No period at the end
- Maximum 72 characters

### Body Guidelines

- Wrap at 72 characters
- Explain what and why, not how
- Reference issues: `Closes #123`, `Fixes #456`

## Branch Naming

### Format

```
<type>/<short-description>
```

### Types

| Prefix | Purpose |
|--------|---------|
| `feature/` | New features |
| `fix/` | Bug fixes |
| `docs/` | Documentation updates |
| `refactor/` | Code refactoring |
| `test/` | Test additions/changes |
| `chore/` | Maintenance tasks |

### Examples

```bash
# Feature branches
git checkout -b feature/prompt-versioning
git checkout -b feature/api-pagination

# Fix branches
git checkout -b fix/storage-race-condition
git checkout -b fix/ui-loading-state

# Documentation
git checkout -b docs/api-examples

# Refactoring
git checkout -b refactor/extract-validators
```

### Rules

- Use lowercase with hyphens as separators
- Keep names descriptive but concise (under 50 chars)
- Include issue number if applicable: `feature/123-prompt-search`

## Pull Request Process

### Before Creating a PR

1. **Run tests:**
   ```bash
   pytest
   ```

2. **Check code style:**
   ```bash
   ruff check .
   ruff format --check .
   ```

3. **Update documentation** if needed

4. **Ensure commits are clean:**
   - Squash fixup commits
   - Rebase on main if needed

### Creating a PR

1. **Push your branch:**
   ```bash
   git push origin feature/my-feature
   ```

2. **Open PR on GitHub** with:
   - Clear title following commit conventions
   - Detailed description including:
     - What changed and why
     - How to test
     - Screenshots (for UI changes)
     - Related issues

3. **Request reviewers** (at least one)

### PR Template

```markdown
## Summary
Brief description of changes

## Changes
- Change 1
- Change 2
- Change 3

## Testing
- [ ] Unit tests pass
- [ ] Integration tests pass
- [ ] Manual testing completed

## Screenshots
(if applicable)

## Related Issues
Closes #123
```

## Review Guidelines

### For Authors

- Respond to all comments
- Make requested changes in new commits (don't force push)
- Resolve conversations when addressed
- Re-request review when ready

### For Reviewers

- Review within 24-48 hours
- Be constructive and specific
- Approve when satisfied, don't just "LGTM"
- Test the changes locally if significant

### Review Checklist

- [ ] Code follows style guide
- [ ] Functions are appropriately sized
- [ ] Error handling is comprehensive
- [ ] Tests cover new functionality
- [ ] Documentation is updated
- [ ] No obvious security issues
- [ ] Performance considerations addressed

## Questions?

If you have questions about contributing:

1. Check existing documentation
2. Search closed issues/PRs
3. Ask in a new issue with the `question` label

Thank you for contributing to Prompt Governor!
