# Dockerfile for Tablewrite Backend
# D&D Module Assistant with WebSocket support for FoundryVTT
#
# Build targets:
#   - production (default): Minimal image for running backend
#   - test: Full image with tests and data for running pytest
#
# Usage:
#   Production: docker build -t tablewrite .
#   Testing:    docker build --target test -t tablewrite-test .

FROM python:3.11-slim AS base

WORKDIR /app

# Install system dependencies
# - tesseract-ocr: OCR for PDF text extraction fallback
# - poppler-utils: PDF processing utilities (pdfinfo, pdftotext)
# - libgl1: OpenCV dependency
# - libglib2.0-0: OpenCV dependency
# - curl: for healthcheck
RUN apt-get update && apt-get install -y --no-install-recommends \
    tesseract-ocr \
    poppler-utils \
    libgl1 \
    libglib2.0-0 \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install uv for dependency management
RUN pip install --no-cache-dir uv

# Copy dependency files first (for layer caching)
COPY pyproject.toml uv.lock ./

# ============================================
# Production target (default)
# ============================================
FROM base AS production

# Install Python dependencies (no dev dependencies)
RUN uv sync --frozen --no-dev

# Copy application code
COPY src/ ./src/
COPY ui/ ./ui/

# Create output directories
RUN mkdir -p /app/output /app/data

# Set PYTHONPATH so backend can import from src/ and find app module
ENV PYTHONPATH=/app/src:/app/ui/backend

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Run backend from ui/backend directory
WORKDIR /app/ui/backend
CMD ["uv", "run", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]

# ============================================
# Test target
# ============================================
FROM base AS test

# Install ALL dependencies (including dev/test)
RUN uv sync --frozen

# Copy application code
COPY src/ ./src/
COPY ui/ ./ui/

# Copy test infrastructure
COPY tests/ ./tests/
COPY pytest.ini ./

# Copy scripts (needed for some tests)
COPY scripts/ ./scripts/

# Copy test data (PDFs needed for tests)
COPY data/ ./data/

# Create output directories
RUN mkdir -p /app/output /app/tests/output /app/tests/test_runs

# Create non-root user for testing (root bypasses file permissions)
RUN useradd -m -s /bin/bash testuser && \
    chown -R testuser:testuser /app

# Switch to non-root user
USER testuser

# Set environment for testing
ENV PYTHONPATH=/app/src:/app
ENV CI=true
ENV SKIP_FOUNDRY_INIT=true

# Default command runs smoke tests
CMD ["uv", "run", "pytest", "-v", "--tb=short"]
