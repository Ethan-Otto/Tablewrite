"""Tool system initialization."""
from .base import BaseTool, ToolSchema, ToolResponse
from .registry import ToolRegistry, registry
from .image_generator import ImageGeneratorTool
from .actor_creator import ActorCreatorTool
from .batch_actor_creator import BatchActorCreatorTool
from .actor_editor import ActorEditorTool
from .journal_creator import JournalCreatorTool
from .scene_creator import SceneCreatorTool
from .asset_deleter import AssetDeleterTool
from .journal_query import JournalQueryTool
from .list_actors import ListActorsTool
from .list_scenes import ListScenesTool
from .help import HelpTool

# Auto-register tools
registry.register(ImageGeneratorTool())
registry.register(ActorCreatorTool())
registry.register(BatchActorCreatorTool())
registry.register(ActorEditorTool())
registry.register(JournalCreatorTool())
registry.register(SceneCreatorTool())
registry.register(AssetDeleterTool())
registry.register(JournalQueryTool())
registry.register(ListActorsTool())
registry.register(ListScenesTool())
registry.register(HelpTool())

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
    'SceneCreatorTool',
    'AssetDeleterTool',
    'JournalQueryTool',
    'ListActorsTool',
    'ListScenesTool',
    'HelpTool',
]
