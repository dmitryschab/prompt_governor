"""FastAPI application entry point for Prompt Governor MVP."""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
import os

from mvp.api import configs, documents

app = FastAPI(
    title="Prompt Governor",
    description="Lightweight prompt optimization tool for contract extraction",
    version="0.1.0",
)

# Include API routers
app.include_router(configs.router)
app.include_router(documents.router)

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


# Mount static files (frontend)
static_dir = os.path.join(os.path.dirname(__file__), "..", "static")
if os.path.exists(static_dir):
    app.mount("/static", StaticFiles(directory=static_dir), name="static")

    @app.get("/")
    async def serve_index():
        """Serve the frontend index page."""
        return FileResponse(os.path.join(static_dir, "index.html"))


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000, reload=True)

# Hot reload test
