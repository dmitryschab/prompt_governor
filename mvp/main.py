"""FastAPI application entry point for Prompt Governor MVP."""

import logging
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from mvp.api import api_router
from mvp.services.storage import get_collection_path
from mvp.utils.errors import register_exception_handlers
from mvp.utils.cache import get_cache_stats

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan handler for startup and shutdown events."""
    # Startup: Ensure data directories exist
    logger.info("Starting up Prompt Governor MVP...")

    collections = ["prompts", "configs", "runs"]
    for collection in collections:
        try:
            path = get_collection_path(collection)
            path.mkdir(parents=True, exist_ok=True)
            logger.info(f"Ensured directory exists: {path}")
        except Exception as e:
            logger.error(f"Failed to create directory for {collection}: {e}")

    logger.info("Startup complete. Prompt Governor MVP ready.")
    yield
    # Shutdown
    logger.info("Shutting down Prompt Governor MVP...")


app = FastAPI(
    title="Prompt Governor",
    description="Lightweight prompt optimization tool for contract extraction",
    version="0.1.0",
    lifespan=lifespan,
)

# Register exception handlers
register_exception_handlers(app)

# Add GZip compression middleware (compress responses > 1KB)
app.add_middleware(GZipMiddleware, minimum_size=1000)

# Include API router
app.include_router(api_router)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # For development
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Health check endpoint
@app.get("/api/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "version": "0.1.0"}


# Test endpoint for volume mounts
@app.get("/api/test/volumes")
async def test_volumes():
    """Test endpoint to verify volume mounts."""
    volumes = {
        "data": os.path.exists("/app/data"),
        "documents": os.path.exists("/app/documents"),
        "ground_truth": os.path.exists("/app/ground_truth"),
        "cache": os.path.exists("/app/cache"),
        "mvp": os.path.exists("/app/mvp"),
        "prompt_optimization": os.path.exists("/app/prompt_optimization"),
    }
    return {"volumes_mounted": volumes, "all_mounted": all(volumes.values())}


# Cache control headers for static files
CACHE_CONTROL_STATIC = "public, max-age=86400"  # 1 day for static assets
CACHE_CONTROL_INDEX = "no-cache"  # No cache for HTML


class CachedStaticFiles(StaticFiles):
    """StaticFiles with cache headers."""

    async def get_response(self, path: str, scope):
        response = await super().get_response(path, scope)

        # Add cache headers based on file type
        if path.endswith(
            (".js", ".css", ".png", ".jpg", ".jpeg", ".gif", ".ico", ".woff", ".woff2")
        ):
            response.headers["Cache-Control"] = CACHE_CONTROL_STATIC
        elif path.endswith(".html") or path == "":
            response.headers["Cache-Control"] = CACHE_CONTROL_INDEX

        return response


# Mount static files (frontend) with caching
static_dir = os.path.join(os.path.dirname(__file__), "..", "static")
if os.path.exists(static_dir):
    app.mount("/static", CachedStaticFiles(directory=static_dir), name="static")

    @app.get("/")
    async def serve_index():
        """Serve the frontend index page."""
        response = FileResponse(
            os.path.join(static_dir, "index.html"),
            headers={"Cache-Control": CACHE_CONTROL_INDEX},
        )
        return response


# Performance monitoring endpoint
@app.get("/api/performance/cache-stats")
async def cache_statistics():
    """Get cache statistics for monitoring."""
    return await get_cache_stats()


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000, reload=True)
