"""FoundryVTT Actor operations."""

import logging
import requests
from typing import Optional, Dict, Any, List

logger = logging.getLogger(__name__)


class ActorManager:
    """Manages actor operations for FoundryVTT."""

    def __init__(self, relay_url: str, foundry_url: str, api_key: str, client_id: str):
        """
        Initialize actor manager.

        Args:
            relay_url: URL of the relay server
            foundry_url: URL of the FoundryVTT instance
            api_key: API key for authentication
            client_id: Client ID for the FoundryVTT instance
        """
        self.relay_url = relay_url
        self.foundry_url = foundry_url
        self.api_key = api_key
        self.client_id = client_id

    def search_all_compendiums(self, name: str) -> Optional[str]:
        """
        Search all user compendiums for actor by name.

        Args:
            name: Actor name to search for

        Returns:
            Actor UUID if found, None otherwise
        """
        url = f"{self.relay_url}/search"

        headers = {
            "x-api-key": self.api_key,
            "Content-Type": "application/json"
        }

        # Use filter parameter (not type) for Actor filtering
        params = {
            "clientId": self.client_id,
            "filter": "Actor",
            "query": name
        }

        logger.debug(f"Searching for actor: {name}")

        try:
            response = requests.get(url, params=params, headers=headers, timeout=30)

            if response.status_code != 200:
                logger.warning(f"Actor search failed: {response.status_code}")
                return None

            results = response.json()

            # Handle empty results
            if not results or (isinstance(results, dict) and results.get("error")):
                logger.debug(f"No actor found with name: {name}")
                return None

            # Handle both list and dict response formats
            search_results = results if isinstance(results, list) else results.get("results", [])

            # Find exact name match
            for actor in search_results:
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

        Args:
            stat_block: Parsed StatBlock object

        Returns:
            Actor UUID

        Raises:
            RuntimeError: If creation fails
        """
        url = f"{self.relay_url}/create?clientId={self.client_id}"

        headers = {
            "x-api-key": self.api_key,
            "Content-Type": "application/json"
        }

        # Map stat block to D&D 5e Actor structure
        actor_data = {
            "name": stat_block.name,
            "type": "npc",
            "system": {
                "attributes": {
                    "ac": {"value": stat_block.armor_class},
                    "hp": {
                        "value": stat_block.hit_points,
                        "max": stat_block.hit_points
                    }
                },
                "details": {
                    "cr": stat_block.challenge_rating,
                    "type": {
                        "value": stat_block.type or "",
                        "subtype": ""
                    },
                    "alignment": stat_block.alignment or "",
                    "biography": {
                        "value": f"<pre>{stat_block.raw_text}</pre>"
                    }
                }
            }
        }

        # Add abilities if present
        if stat_block.abilities:
            actor_data["system"]["abilities"] = {
                ability.lower(): {"value": value}
                for ability, value in stat_block.abilities.items()
            }

        payload = {
            "entityType": "Actor",
            "data": actor_data
        }

        logger.debug(f"Creating creature actor: {stat_block.name}")

        try:
            response = requests.post(url, json=payload, headers=headers, timeout=30)

            if response.status_code != 200:
                logger.error(f"Failed to create actor: {response.status_code} - {response.text}")
                raise RuntimeError(
                    f"Failed to create actor: {response.status_code} - {response.text}"
                )

            result = response.json()
            uuid = result.get("uuid")
            logger.info(f"Created creature actor: {stat_block.name} (UUID: {uuid})")
            return uuid

        except requests.exceptions.RequestException as e:
            logger.error(f"Actor creation request failed: {e}")
            raise RuntimeError(f"Failed to create actor: {e}") from e

    def create_npc_actor(self, npc, stat_block_uuid: Optional[str] = None) -> str:
        """
        Create an NPC Actor with biography and optional stat block link.

        NPCs are bio-only Actors with no stats. If stat_block_uuid provided,
        biography includes @UUID link to the creature's stat block.

        Args:
            npc: NPC object with description and plot info
            stat_block_uuid: Optional UUID of creature stat block actor

        Returns:
            Actor UUID

        Raises:
            RuntimeError: If creation fails
        """
        url = f"{self.relay_url}/create?clientId={self.client_id}"

        headers = {
            "x-api-key": self.api_key,
            "Content-Type": "application/json"
        }

        # Build biography HTML
        bio_parts = [
            f"<h2>{npc.name}</h2>",
            f"<p><strong>Description:</strong> {npc.description}</p>",
            f"<p><strong>Plot Role:</strong> {npc.plot_relevance}</p>"
        ]

        if npc.location:
            bio_parts.append(f"<p><strong>Location:</strong> {npc.location}</p>")

        if stat_block_uuid:
            bio_parts.append(
                f'<p><strong>Creature Stats:</strong> '
                f'@UUID[{stat_block_uuid}]{{View {npc.creature_stat_block_name} stats}}</p>'
            )

        bio_html = "\n".join(bio_parts)

        # Create bio-only NPC actor (no stats)
        actor_data = {
            "name": npc.name,
            "type": "npc",
            "system": {
                "details": {
                    "biography": {
                        "value": bio_html
                    }
                }
            }
        }

        payload = {
            "entityType": "Actor",
            "data": actor_data
        }

        logger.debug(f"Creating NPC actor: {npc.name}")

        try:
            response = requests.post(url, json=payload, headers=headers, timeout=30)

            if response.status_code != 200:
                logger.error(f"Failed to create NPC: {response.status_code} - {response.text}")
                raise RuntimeError(
                    f"Failed to create NPC: {response.status_code} - {response.text}"
                )

            result = response.json()
            uuid = result.get("uuid")
            logger.info(f"Created NPC actor: {npc.name} (UUID: {uuid})")
            return uuid

        except requests.exceptions.RequestException as e:
            logger.error(f"NPC creation request failed: {e}")
            raise RuntimeError(f"Failed to create NPC: {e}") from e

    def create_actor(self, actor_data: Dict[str, Any]) -> str:
        """
        Create an Actor from pre-built FoundryVTT JSON format.

        This method accepts a complete FoundryVTT actor JSON structure
        (as produced by convert_to_foundry) and uploads it to FoundryVTT.

        Args:
            actor_data: Complete FoundryVTT actor JSON with 'name', 'type',
                       'system', 'items', etc.

        Returns:
            Actor UUID

        Raises:
            RuntimeError: If creation fails
        """
        url = f"{self.relay_url}/create?clientId={self.client_id}"

        headers = {
            "x-api-key": self.api_key,
            "Content-Type": "application/json"
        }

        payload = {
            "entityType": "Actor",
            "data": actor_data
        }

        actor_name = actor_data.get("name", "Unknown")
        logger.debug(f"Creating actor: {actor_name}")

        try:
            response = requests.post(url, json=payload, headers=headers, timeout=30)

            if response.status_code != 200:
                logger.error(f"Failed to create actor: {response.status_code} - {response.text}")
                raise RuntimeError(
                    f"Failed to create actor: {response.status_code} - {response.text}"
                )

            result = response.json()
            uuid = result.get("uuid")
            logger.info(f"Created actor: {actor_name} (UUID: {uuid})")
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
        url = f"{self.relay_url}/get?clientId={self.client_id}&uuid={actor_uuid}"

        headers = {
            "x-api-key": self.api_key,
            "Content-Type": "application/json"
        }

        logger.debug(f"Retrieving actor: {actor_uuid}")

        try:
            response = requests.get(url, headers=headers, timeout=30)

            if response.status_code != 200:
                logger.error(f"Failed to retrieve actor: {response.status_code} - {response.text}")
                raise RuntimeError(
                    f"Failed to retrieve actor: {response.status_code} - {response.text}"
                )

            response_data = response.json()

            # Extract actor data from response envelope
            actor_data = response_data.get("data", response_data)

            actor_name = actor_data.get("name", "Unknown")
            logger.info(f"Retrieved actor: {actor_name} (UUID: {actor_uuid})")
            return actor_data

        except requests.exceptions.RequestException as e:
            logger.error(f"Actor retrieval request failed: {e}")
            raise RuntimeError(f"Failed to retrieve actor: {e}") from e
