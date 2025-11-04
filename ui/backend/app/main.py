"""D&D Module Assistant API."""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pathlib import Path
from app.routers import chat
from app.config import settings

app = FastAPI(
    title="D&D Module Assistant API",
    description="Backend API for D&D module generation and management",
    version="0.1.0"
)

# CORS middleware for local development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:5174"],  # Vite ports
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register routers
app.include_router(chat.router)


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "service": "module-assistant-api"}


@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "message": "D&D Module Assistant API",
        "docs": "/docs",
        "health": "/health"
    }


@app.get("/api/images/{filename}")
async def serve_image(filename: str):
    """
    Serve generated images from chat_images directory.

    Args:
        filename: Image filename

    Returns:
        Image file

    Raises:
        HTTPException: If file not found or invalid filename
    """
    # Security: validate filename (no path traversal)
    if ".." in filename or "/" in filename or "\\" in filename:
        raise HTTPException(status_code=400, detail="Invalid filename")

    # Only serve .png files
    if not filename.endswith(".png"):
        raise HTTPException(status_code=400, detail="Only PNG files supported")

    file_path = settings.IMAGE_OUTPUT_DIR / filename

    if not file_path.exists():
        raise HTTPException(status_code=404, detail="Image not found")

    return FileResponse(file_path, media_type="image/png")
