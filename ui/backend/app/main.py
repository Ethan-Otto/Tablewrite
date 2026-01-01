"""D&D Module Assistant API."""

from fastapi import FastAPI, HTTPException, WebSocket
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pathlib import Path
from dotenv import load_dotenv
from app.routers import actors, chat, health, journals, search
from app.config import settings
from app.websocket import foundry_websocket_endpoint


# Load environment variables from project root .env
project_root = Path(__file__).parent.parent.parent.parent
env_path = project_root / ".env"
if env_path.exists():
    load_dotenv(env_path)
else:
    # Fallback to backend .env
    load_dotenv()

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
app.include_router(health.router)
app.include_router(chat.router)
app.include_router(actors.router)
app.include_router(journals.router)
app.include_router(search.router)


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


@app.websocket("/ws/foundry")
async def websocket_foundry(websocket: WebSocket):
    """WebSocket endpoint for Foundry module connections."""
    await foundry_websocket_endpoint(websocket)


