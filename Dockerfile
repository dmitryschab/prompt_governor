# Prompt Governor - MVP Dockerfile
# Phase A1: Docker Setup

FROM python:3.13-slim

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy requirements first (for better caching)
COPY requirements.mvp.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.mvp.txt

# Copy application code
# Note: In development, this will be overridden by volume mounts
COPY . .

# Expose FastAPI default port
EXPOSE 8000

# Configure hot reload for development
# Uses uvicorn with --reload flag for automatic code reloading
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000", "--reload", "--reload-dir", "/app"]
