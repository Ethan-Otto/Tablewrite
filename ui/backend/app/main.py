"""D&D Module Assistant API."""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(
    title="D&D Module Assistant API",
    description="Backend API for D&D module generation and management",
    version="0.1.0"
)

# CORS middleware for local development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],  # Vite default port
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


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
