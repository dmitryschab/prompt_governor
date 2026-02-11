"""API router exports for Prompt Governor MVP.

This module provides centralized access to all API routers.

Example:
    from mvp.api import api_router
    app.include_router(api_router)
"""

from fastapi import APIRouter

# Import individual routers
from mvp.api.documents import router as documents_router
from mvp.api.prompts import router as prompts_router

# Create main API router
api_router = APIRouter(prefix="/api")

# Include sub-routers
api_router.include_router(documents_router)
api_router.include_router(prompts_router)

__all__ = ["api_router", "documents_router", "prompts_router"]
