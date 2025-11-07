"""Tool system initialization."""
from .base import BaseTool, ToolSchema, ToolResponse
from .registry import ToolRegistry, registry
from .image_generator import ImageGeneratorTool
from .actor_creator import ActorCreatorTool

# Auto-register tools
registry.register(ImageGeneratorTool())
registry.register(ActorCreatorTool())

__all__ = [
    'BaseTool',
    'ToolSchema',
    'ToolResponse',
    'ToolRegistry',
    'registry',
    'ImageGeneratorTool',
    'ActorCreatorTool'
]
