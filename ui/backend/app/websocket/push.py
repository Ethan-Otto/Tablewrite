"""Push notification helpers for broadcasting to Foundry clients."""
from typing import Dict, Any
from .foundry_endpoint import foundry_manager


async def push_actor(actor_data: Dict[str, Any]) -> None:
    """
    Push an actor to all connected Foundry clients.

    Args:
        actor_data: FoundryVTT actor data object
    """
    await foundry_manager.broadcast({
        "type": "actor",
        "data": actor_data
    })


async def push_journal(journal_data: Dict[str, Any]) -> None:
    """
    Push a journal entry to all connected Foundry clients.

    Args:
        journal_data: FoundryVTT journal data object
    """
    await foundry_manager.broadcast({
        "type": "journal",
        "data": journal_data
    })


async def push_scene(scene_data: Dict[str, Any]) -> None:
    """
    Push a scene to all connected Foundry clients.

    Args:
        scene_data: FoundryVTT scene data object
    """
    await foundry_manager.broadcast({
        "type": "scene",
        "data": scene_data
    })
