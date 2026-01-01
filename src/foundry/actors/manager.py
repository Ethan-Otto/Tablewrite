"""FoundryVTT Actor operations via WebSocket backend."""

import logging
import requests
from typing import Optional, Dict, Any, List

logger = logging.getLogger(__name__)


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

    def create_npc_actor(self, npc, stat_block_uuid: Optional[str] = None) -> str:
        """
        Create an NPC Actor with biography and optional stat block link.

        NOTE: This method requires a backend endpoint for raw actor creation.

        Args:
            npc: NPC object with description and plot info
            stat_block_uuid: Optional UUID of creature stat block actor

        Returns:
            Actor UUID

        Raises:
            NotImplementedError: Raw actor creation endpoint not yet implemented
        """
        raise NotImplementedError(
            "Raw NPC creation via WebSocket backend not yet implemented. "
            "Use create_actor() with actor_data dict instead."
        )

    def create_actor(self, actor_data: Dict[str, Any], spell_uuids: list[str] = None) -> str:
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

        try:
            response = requests.post(
                endpoint,
                json={"actor": actor_data},
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
