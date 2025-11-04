"""Base classes for tool system."""
from abc import ABC, abstractmethod
from typing import Dict, Any
from pydantic import BaseModel


class ToolSchema(BaseModel):
    """Schema for tool definition (Gemini function calling format)."""
    name: str
    description: str
    parameters: Dict[str, Any]  # JSON Schema format


class ToolResponse(BaseModel):
    """Standard tool response format."""
    type: str  # "text", "image", "scene", "error", etc.
    message: str
    data: Dict[str, Any] | None = None


class BaseTool(ABC):
    """Base class for all tools."""

    @abstractmethod
    def get_schema(self) -> ToolSchema:
        """Return the tool schema for Gemini function calling."""
        pass

    @abstractmethod
    async def execute(self, **kwargs) -> ToolResponse:
        """Execute the tool with given parameters."""
        pass

    @property
    @abstractmethod
    def name(self) -> str:
        """Tool name (must match schema name)."""
        pass
