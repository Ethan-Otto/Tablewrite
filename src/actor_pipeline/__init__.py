"""Actor creation pipeline.

This module handles the generation, parsing, and orchestration of actor creation.
For FoundryVTT CRUD operations, see src/foundry/actors/.

Pipeline:
    Description -> StatBlock text -> StatBlock model -> ParsedActorData -> FoundryVTT JSON

Usage:
    # Import models directly
    from actor_pipeline.models import StatBlock, NPC, ActorCreationResult

    # Import orchestration functions directly to avoid circular imports
    from actor_pipeline.orchestrate import create_actor_from_description_sync
"""

from .models import StatBlock, NPC, ActorCreationResult

__all__ = [
    "StatBlock",
    "NPC",
    "ActorCreationResult",
]
