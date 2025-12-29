"""Tool system initialization."""
from .base import BaseTool, ToolSchema, ToolResponse
from .registry import ToolRegistry, registry
from .image_generator import ImageGeneratorTool
from .actor_creator import ActorCreatorTool
from .journal_creator import JournalCreatorTool
from .scene_creator import SceneCreatorTool

# Auto-register tools
registry.register(ImageGeneratorTool())
registry.register(ActorCreatorTool())
registry.register(JournalCreatorTool())
registry.register(SceneCreatorTool())

__all__ = [
    'BaseTool',
    'ToolSchema',
    'ToolResponse',
    'ToolRegistry',
    'registry',
    'ImageGeneratorTool',
    'ActorCreatorTool',
    'JournalCreatorTool',
    'SceneCreatorTool'
]
