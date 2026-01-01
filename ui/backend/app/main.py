"""D&D Module Assistant API."""

from fastapi import FastAPI, WebSocket
from fastapi.middleware.cors import CORSMiddleware
from pathlib import Path
from dotenv import load_dotenv

from app.routers import actors, chat, files, health, journals, search
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
app.include_router(files.router)


@app.websocket("/ws/foundry")
async def websocket_foundry(websocket: WebSocket):
    """WebSocket endpoint for Foundry module connections."""
    await foundry_websocket_endpoint(websocket)


