"""Health and status endpoints."""

from fastapi import APIRouter
from app.websocket import foundry_manager

router = APIRouter(tags=["health"])


@router.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "service": "module-assistant-api"}


@router.get("/")
async def root():
    """Root endpoint."""
    return {
        "message": "D&D Module Assistant API",
        "docs": "/docs",
        "health": "/health"
    }


@router.get("/api/foundry/status")
async def foundry_status():
    """Check Foundry WebSocket connection status."""
    return {
        "connected_clients": foundry_manager.connection_count,
        "status": "connected" if foundry_manager.connection_count > 0 else "disconnected"
    }
