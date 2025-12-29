# Dockerfile for Tablewrite Backend
# D&D Module Assistant with WebSocket support for FoundryVTT
FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
# - tesseract-ocr: OCR for PDF text extraction fallback
# - poppler-utils: PDF processing utilities
# - curl: for healthcheck
RUN apt-get update && apt-get install -y --no-install-recommends \
    tesseract-ocr \
    poppler-utils \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install uv for dependency management
RUN pip install --no-cache-dir uv

# Copy dependency files first (for layer caching)
COPY pyproject.toml uv.lock ./

# Install Python dependencies
RUN uv sync --frozen --no-dev

# Copy application code
COPY src/ ./src/
COPY ui/ ./ui/

# Create output directories
RUN mkdir -p /app/output /app/data

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Run backend using uv
# Note: Using the full path to main module
CMD ["uv", "run", "uvicorn", "ui.backend.app.main:app", "--host", "0.0.0.0", "--port", "8000"]
