"""Chat models for D&D Module Assistant."""

from datetime import datetime
from enum import Enum
from typing import Optional, Dict, Any, List
from pydantic import BaseModel, Field


class ChatRole(str, Enum):
    """Chat message role."""
    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"


class ChatMessage(BaseModel):
    """Single chat message."""
    role: ChatRole
    content: str
    timestamp: datetime = Field(default_factory=datetime.now)


class ChatRequest(BaseModel):
    """Request to chat endpoint."""
    message: str = Field(..., min_length=1, max_length=10000)
    context: Dict[str, Any] = Field(default_factory=dict)
    conversation_history: List[ChatMessage] = Field(default_factory=list)


class ChatResponse(BaseModel):
    """Response from chat endpoint."""
    message: str
    type: str  # "text", "scene", "list", "error"
    data: Optional[Dict[str, Any]] = None
    scene: Optional[Any] = None  # Will reference Scene model
