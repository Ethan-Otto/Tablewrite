"""D&D Module Assistant API."""

import asyncio
import logging
import os
import sys

from fastapi import FastAPI, WebSocket
from fastapi.middleware.cors import CORSMiddleware
from pathlib import Path
from dotenv import load_dotenv

from app.routers import actors, chat, files, folders, health, journals, modules, scenes, search
from app.routers.scenes import scene_upload_router
from app.websocket import foundry_websocket_endpoint
from app.websocket.push import set_main_loop


# Configure logging - show all INFO and above from app modules
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(name)s] %(levelname)s: %(message)s',
    datefmt='%H:%M:%S',
    stream=sys.stdout,
    force=True  # Override any existing config
)

# Ensure app.tools loggers are set to INFO
logging.getLogger('app.tools').setLevel(logging.INFO)
logging.getLogger('app.tools.actor_creator').setLevel(logging.INFO)
logging.getLogger('app.tools.image_generator').setLevel(logging.INFO)


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
foundry_url = os.getenv("FOUNDRY_URL", "http://localhost:30000")
app.add_middleware(
    CORSMiddleware,
    allow_origins=[foundry_url],  # Foundry
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register routers
app.include_router(health.router)
app.include_router(chat.router)
app.include_router(actors.router)
app.include_router(journals.router)
app.include_router(modules.router)
app.include_router(search.router)
app.include_router(files.router)
app.include_router(folders.router)
app.include_router(scenes.router)
app.include_router(scene_upload_router)


@app.websocket("/ws/foundry")
async def websocket_foundry(websocket: WebSocket):
    """WebSocket endpoint for Foundry module connections."""
    await foundry_websocket_endpoint(websocket)


@app.on_event("startup")
async def startup_event():
    """Store main event loop reference for cross-thread progress broadcasts."""
    set_main_loop(asyncio.get_event_loop())
