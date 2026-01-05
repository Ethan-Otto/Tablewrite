"""Tool system initialization."""
from .base import BaseTool, ToolSchema, ToolResponse
from .registry import ToolRegistry, registry
from .image_generator import ImageGeneratorTool
from .actor_creator import ActorCreatorTool
from .batch_actor_creator import BatchActorCreatorTool
from .actor_editor import ActorEditorTool
from .journal_creator import JournalCreatorTool
from .scene_creator import SceneCreatorTool

# Auto-register tools
registry.register(ImageGeneratorTool())
registry.register(ActorCreatorTool())
registry.register(BatchActorCreatorTool())
registry.register(ActorEditorTool())
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
    'BatchActorCreatorTool',
    'ActorEditorTool',
    'JournalCreatorTool',
    'SceneCreatorTool'
]
