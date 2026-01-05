"""FoundryVTT Actor operations via WebSocket backend."""

import asyncio
import logging
import requests
from typing import Optional, Dict, Any, List

logger = logging.getLogger(__name__)


def _run_async(coro):
    """Run async coroutine from sync context."""
    try:
        asyncio.get_running_loop()  # Check if there's a running loop
        # We're in an async context, use nest_asyncio or run in thread
        import concurrent.futures
        with concurrent.futures.ThreadPoolExecutor() as pool:
            future = pool.submit(asyncio.run, coro)
            return future.result()
    except RuntimeError:
        # No running loop, we can use asyncio.run directly
        return asyncio.run(coro)


class ActorManager:
    """Manages actor operations for FoundryVTT via WebSocket backend.

    All operations go through the FastAPI backend HTTP API, which internally
    uses WebSocket to communicate with FoundryVTT. The relay server is no longer used.
    """

    def __init__(self, backend_url: str):
        """
        Initialize actor manager.

        Args:
            backend_url: URL of the FastAPI backend (e.g., http://localhost:8000)
        """
        self.backend_url = backend_url

    def search_all_compendiums(self, name: str) -> Optional[str]:
        """
        Search all compendiums for actor by name.

        Args:
            name: Actor name to search for

        Returns:
            Actor UUID if found, None otherwise
        """
        endpoint = f"{self.backend_url}/api/foundry/search"

        params = {
            "query": name,
            "document_type": "Actor"
        }

        logger.debug(f"Searching for actor: {name}")

        try:
            response = requests.get(endpoint, params=params, timeout=30)

            if response.status_code != 200:
                logger.warning(f"Actor search failed: {response.status_code}")
                return None

            data = response.json()

            if not data.get("success"):
                logger.debug(f"No actor found with name: {name}")
                return None

            results = data.get("results", [])

            # Find exact name match
            for actor in results:
                if actor.get("name") == name:
                    uuid = actor.get("uuid")
                    logger.debug(f"Found actor: {name} (UUID: {uuid})")
                    return uuid

            logger.debug(f"No exact match found for actor: {name}")
            return None

        except Exception as e:
            logger.warning(f"Actor search request failed: {e}")
            return None

    def create_creature_actor(self, stat_block) -> str:
        """
        Create a creature Actor from a stat block.

        NOTE: This method requires a backend endpoint for raw actor creation.
        For now, use the /api/actors/create endpoint with a description instead.

        Args:
            stat_block: Parsed StatBlock object

        Returns:
            Actor UUID

        Raises:
            NotImplementedError: Raw actor creation endpoint not yet implemented
        """
        raise NotImplementedError(
            "Raw actor creation via WebSocket backend not yet implemented. "
            "Use create_actor() with actor_data dict, or /api/actors/create with description."
        )

    def create_npc_actor(
        self,
        npc,
        stat_block_uuid: Optional[str] = None,
        stat_block: Optional[Any] = None,
        spell_cache: Optional[Any] = None,
        folder: Optional[str] = None
    ) -> str:
        """
        Create an NPC Actor with biography and optional stat block stats.

        If a stat_block is provided, uses the full conversion pipeline to
        create a complete actor with all stats, attacks, traits, etc.
        Otherwise creates a minimal NPC with just biography.

        Args:
            npc: NPC object with description and plot info
            stat_block_uuid: Optional UUID of creature stat block actor (for linking)
            stat_block: Optional StatBlock object to use for full stats
            spell_cache: Optional SpellCache for spell UUID resolution
            folder: Optional folder ID to place the actor in

        Returns:
            Actor UUID
        """
        # Build biography HTML
        bio_parts = []

        # Add stat block link if provided
        if stat_block_uuid:
            bio_parts.append(
                f'<p><strong>Stat Block:</strong> @UUID[{stat_block_uuid}]</p>'
            )

        # Add description
        if npc.description:
            bio_parts.append(f'<p>{npc.description}</p>')

        # Add plot relevance
        if npc.plot_relevance:
            bio_parts.append(f'<p><strong>Plot Relevance:</strong> {npc.plot_relevance}</p>')

        # Add location if present
        if hasattr(npc, 'location') and npc.location:
            bio_parts.append(f'<p><strong>Location:</strong> {npc.location}</p>')

        # Add first appearance if present
        if hasattr(npc, 'first_appearance_section') and npc.first_appearance_section:
            bio_parts.append(f'<p><strong>First Appearance:</strong> {npc.first_appearance_section}</p>')

        biography_html = '\n'.join(bio_parts)

        # If we have a stat_block_uuid but no local stat_block, fetch from Foundry
        # This handles NPCs that reference compendium creatures (e.g., Klarg → Bugbear)
        if stat_block is None and stat_block_uuid is not None:
            logger.info(f"Fetching creature stats from compendium for NPC: {npc.name} ({stat_block_uuid})")
            try:
                creature_data = self.get_actor(stat_block_uuid)
                if creature_data:
                    # Create a copy of the creature's actor data
                    actor_data = dict(creature_data)

                    # Override name with NPC name
                    actor_data["name"] = npc.name

                    # Keep the creature's image/profile art
                    # (already in actor_data from the fetch)

                    # Add/update biography with NPC-specific info
                    if "system" not in actor_data:
                        actor_data["system"] = {}
                    if "details" not in actor_data["system"]:
                        actor_data["system"]["details"] = {}
                    actor_data["system"]["details"]["biography"] = {"value": biography_html}

                    # Remove _id to create a new actor (not update existing)
                    actor_data.pop("_id", None)
                    actor_data.pop("folder", None)  # Will be set by create_actor

                    logger.info(f"Creating NPC '{npc.name}' with stats copied from '{creature_data.get('name', 'unknown')}'")
                    return self.create_actor(actor_data, folder=folder)
            except Exception as e:
                logger.warning(f"Failed to fetch creature stats for {npc.name}: {e}")
                logger.warning("Falling back to stat_block conversion or minimal creation")

        # If we have a stat block, use full conversion pipeline
        if stat_block is not None:
            logger.info(f"Creating NPC actor with full stats: {npc.name}")
            try:
                # Import here to avoid circular imports
                from foundry_converters.actors.parser import parse_stat_block_parallel
                from foundry_converters.actors.converter import convert_to_foundry

                # Parse stat block to ParsedActorData
                parsed_actor = _run_async(
                    parse_stat_block_parallel(stat_block, spell_cache=spell_cache)
                )

                # Convert to FoundryVTT format
                actor_data, spell_uuids = _run_async(
                    convert_to_foundry(parsed_actor, spell_cache=spell_cache)
                )

                # Override name with NPC name and add biography
                actor_data["name"] = npc.name
                if "system" not in actor_data:
                    actor_data["system"] = {}
                if "details" not in actor_data["system"]:
                    actor_data["system"]["details"] = {}
                actor_data["system"]["details"]["biography"] = {"value": biography_html}

                return self.create_actor(actor_data, spell_uuids=spell_uuids, folder=folder)

            except Exception as e:
                logger.warning(f"Failed to convert stat block for {npc.name}: {e}")
                logger.warning("Falling back to minimal NPC creation")
                # Fall through to minimal creation

        # Minimal NPC actor (no stat block or conversion failed)
        actor_data = {
            "name": npc.name,
            "type": "npc",
            "img": "icons/svg/mystery-man.svg",
            "system": {
                "details": {
                    "biography": {
                        "value": biography_html
                    }
                },
                "attributes": {
                    "hp": {
                        "value": 4,
                        "max": 4
                    }
                }
            },
            "items": []
        }

        logger.info(f"Creating minimal NPC actor: {npc.name}")
        return self.create_actor(actor_data, folder=folder)

    def create_actor(
        self,
        actor_data: Dict[str, Any],
        spell_uuids: Optional[List[str]] = None,
        folder: Optional[str] = None
    ) -> str:
        """
        Create an Actor from pre-built FoundryVTT JSON format.

        This method accepts a complete FoundryVTT actor JSON structure
        (as produced by convert_to_foundry) and uploads it to FoundryVTT
        via the backend's WebSocket connection.

        Args:
            actor_data: Complete FoundryVTT actor JSON with 'name', 'type',
                       'system', 'items', etc.
            spell_uuids: Optional list of compendium spell UUIDs to add
                        (NOTE: not yet implemented via WebSocket)
            folder: Optional folder ID to place the actor in

        Returns:
            Actor UUID

        Raises:
            RuntimeError: If creation fails
        """
        # Use the backend's direct actor push endpoint
        # This bypasses the description-based pipeline and sends raw actor data
        endpoint = f"{self.backend_url}/api/foundry/actor"

        actor_name = actor_data.get("name", "Unknown")
        logger.debug(f"Creating actor: {actor_name}")

        # Build request payload
        payload = {"actor": actor_data}
        if folder:
            payload["folder"] = folder

        try:
            response = requests.post(
                endpoint,
                json=payload,
                timeout=60
            )

            if response.status_code != 200:
                error_detail = response.text
                logger.error(f"Failed to create actor: {response.status_code} - {error_detail}")
                raise RuntimeError(
                    f"Failed to create actor: {response.status_code} - {error_detail}"
                )

            result = response.json()

            if not result.get("success"):
                error = result.get("error", "Unknown error")
                raise RuntimeError(f"Failed to create actor: {error}")

            uuid = result.get("uuid")
            logger.info(f"Created actor: {actor_name} (UUID: {uuid})")

            # Add spells via /give if provided
            if spell_uuids:
                try:
                    self.add_compendium_items(uuid, spell_uuids)
                    logger.info(f"Added {len(spell_uuids)} spells to {actor_name}")
                except Exception as e:
                    logger.warning(f"Failed to add spells to {actor_name}: {e}")
                    # Don't fail the whole operation if spells can't be added

            return uuid

        except requests.exceptions.RequestException as e:
            logger.error(f"Actor creation request failed: {e}")
            raise RuntimeError(f"Failed to create actor: {e}") from e

    def get_actor(self, actor_uuid: str) -> Dict[str, Any]:
        """
        Retrieve an Actor by UUID.

        Args:
            actor_uuid: UUID of the actor to retrieve

        Returns:
            Complete actor data as dict

        Raises:
            RuntimeError: If retrieval fails
        """
        endpoint = f"{self.backend_url}/api/foundry/actor/{actor_uuid}"

        logger.debug(f"Retrieving actor: {actor_uuid}")

        try:
            response = requests.get(endpoint, timeout=30)

            if response.status_code == 404:
                raise RuntimeError(f"Actor not found: {actor_uuid}")

            if response.status_code != 200:
                error_detail = response.text
                logger.error(f"Failed to retrieve actor: {response.status_code} - {error_detail}")
                raise RuntimeError(
                    f"Failed to retrieve actor: {response.status_code} - {error_detail}"
                )

            result = response.json()

            if not result.get("success"):
                raise RuntimeError(f"Failed to retrieve actor: {result.get('error')}")

            actor_data = result.get("entity", {})
            actor_name = actor_data.get("name", "Unknown")
            logger.info(f"Retrieved actor: {actor_name} (UUID: {actor_uuid})")
            return actor_data

        except requests.exceptions.RequestException as e:
            logger.error(f"Actor retrieval request failed: {e}")
            raise RuntimeError(f"Failed to retrieve actor: {e}") from e

    def add_compendium_items(self, actor_uuid: str, item_uuids: list[str]) -> int:
        """
        Add compendium items to an actor.

        Fetches items from compendiums by UUID and adds them to the actor
        using the WebSocket /give message.

        Args:
            actor_uuid: UUID of the actor to add items to
            item_uuids: List of compendium item UUIDs to add

        Returns:
            Number of items successfully added

        Raises:
            RuntimeError: If the request fails
        """
        if not item_uuids:
            return 0

        endpoint = f"{self.backend_url}/api/foundry/actor/{actor_uuid}/items"

        logger.debug(f"Adding {len(item_uuids)} items to actor: {actor_uuid}")

        try:
            response = requests.post(
                endpoint,
                json={"item_uuids": item_uuids},
                timeout=60
            )

            if response.status_code != 200:
                error_detail = response.text
                logger.error(f"Failed to add items: {response.status_code} - {error_detail}")
                raise RuntimeError(
                    f"Failed to add items: {response.status_code} - {error_detail}"
                )

            result = response.json()

            if not result.get("success"):
                raise RuntimeError(f"Failed to add items: {result.get('error')}")

            items_added = result.get("items_added", 0)
            errors = result.get("errors", [])

            if errors:
                logger.warning(f"Some items failed to add: {errors}")

            logger.info(f"Added {items_added} items to actor {actor_uuid}")
            return items_added

        except requests.exceptions.RequestException as e:
            logger.error(f"Add items request failed: {e}")
            raise RuntimeError(f"Failed to add items: {e}") from e

    def get_all_actors(self) -> List[Dict[str, Any]]:
        """
        Get all world actors (not compendium actors).

        Returns:
            List of world actor data dictionaries

        Raises:
            RuntimeError: If request fails
        """
        endpoint = f"{self.backend_url}/api/foundry/actors"

        logger.debug("Retrieving all world actors")

        try:
            response = requests.get(endpoint, timeout=30)

            if response.status_code != 200:
                error_detail = response.text
                logger.error(f"Failed to get actors: {response.status_code} - {error_detail}")
                raise RuntimeError(
                    f"Failed to get actors: {response.status_code} - {error_detail}"
                )

            result = response.json()

            if not result.get("success"):
                raise RuntimeError(f"Failed to get actors: {result.get('error')}")

            actors = result.get("actors", [])
            logger.info(f"Retrieved {len(actors)} world actors")
            return actors

        except requests.exceptions.RequestException as e:
            logger.error(f"Get all actors request failed: {e}")
            raise RuntimeError(f"Failed to get all actors: {e}") from e

    def delete_actor(self, actor_uuid: str) -> Dict[str, Any]:
        """
        Delete an actor.

        Args:
            actor_uuid: UUID of the actor to delete (format: Actor.{id})

        Returns:
            Response data from API

        Raises:
            RuntimeError: If deletion fails
        """
        endpoint = f"{self.backend_url}/api/foundry/actor/{actor_uuid}"

        logger.debug(f"Deleting actor: {actor_uuid}")

        try:
            response = requests.delete(endpoint, timeout=30)

            if response.status_code == 404:
                raise RuntimeError(f"Actor not found: {actor_uuid}")

            if response.status_code != 200:
                error_detail = response.text
                logger.error(f"Delete failed: {response.status_code} - {error_detail}")
                raise RuntimeError(f"Failed to delete actor: {response.status_code} - {error_detail}")

            result = response.json()
            logger.info(f"Deleted actor: {actor_uuid}")
            return result

        except requests.exceptions.RequestException as e:
            logger.error(f"Delete request failed: {e}")
            raise RuntimeError(f"Failed to delete actor: {e}") from e
