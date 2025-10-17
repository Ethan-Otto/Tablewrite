"""FoundryVTT REST API client."""

import os
import logging
import requests
from typing import Literal, Dict, Any, Optional

logger = logging.getLogger(__name__)


class FoundryClient:
    """Client for interacting with FoundryVTT via REST API."""

    def __init__(self, target: Literal["local", "forge"] = "local"):
        """
        Initialize FoundryVTT API client.

        Args:
            target: Target environment ('local' or 'forge')

        Raises:
            ValueError: If required environment variables are not set
        """
        self.target = target
        self.relay_url = os.getenv("FOUNDRY_RELAY_URL")

        if not self.relay_url:
            raise ValueError("FOUNDRY_RELAY_URL not set in environment")

        if target == "local":
            self.foundry_url = os.getenv("FOUNDRY_LOCAL_URL")
            self.api_key = os.getenv("FOUNDRY_LOCAL_API_KEY")
            if not self.foundry_url:
                raise ValueError("FOUNDRY_LOCAL_URL not set in environment")
            if not self.api_key:
                raise ValueError("FOUNDRY_LOCAL_API_KEY not set in environment")
        elif target == "forge":
            self.foundry_url = os.getenv("FOUNDRY_FORGE_URL")
            self.api_key = os.getenv("FOUNDRY_FORGE_API_KEY")
            if not self.foundry_url:
                raise ValueError("FOUNDRY_FORGE_URL not set in environment")
            if not self.api_key:
                raise ValueError("FOUNDRY_FORGE_API_KEY not set in environment")
        else:
            raise ValueError(f"Invalid target: {target}. Must be 'local' or 'forge'")

        logger.info(f"Initialized FoundryClient for {target} at {self.foundry_url}")

    def find_journal_by_name(self, name: str) -> Optional[Dict[str, Any]]:
        """
        Find a journal entry by name.

        Args:
            name: Name of the journal entry to find

        Returns:
            Journal entry dict if found, None otherwise

        Raises:
            RuntimeError: If API request fails
        """
        url = f"{self.relay_url}/search"

        headers = {
            "x-api-key": self.api_key,
            "Content-Type": "application/json"
        }

        params = {
            "type": "JournalEntry",
            "name": name
        }

        logger.debug(f"Searching for journal: {name}")

        try:
            response = requests.get(url, params=params, headers=headers, timeout=30)

            if response.status_code != 200:
                logger.error(f"Search failed: {response.status_code}")
                raise RuntimeError(f"Failed to search journals: {response.status_code}")

            results = response.json()

            if not results:
                logger.debug(f"No journal found with name: {name}")
                return None

            # Return first exact match
            for journal in results:
                if journal.get("name") == name:
                    logger.debug(f"Found journal: {name} (ID: {journal.get('_id')})")
                    return journal

            return None

        except requests.exceptions.RequestException as e:
            logger.error(f"Search request failed: {e}")
            raise RuntimeError(f"Failed to search journals: {e}") from e

    def update_journal_entry(
        self,
        journal_id: str,
        content: str = None,
        name: str = None
    ) -> Dict[str, Any]:
        """
        Update an existing journal entry.

        Args:
            journal_id: ID of the journal entry to update
            content: New HTML content (optional)
            name: New name (optional)

        Returns:
            Dict containing updated journal entry data

        Raises:
            RuntimeError: If API request fails
        """
        url = f"{self.relay_url}/update"

        headers = {
            "x-api-key": self.api_key,
            "Content-Type": "application/json"
        }

        payload = {
            "type": "JournalEntry",
            "id": journal_id,
            "data": {}
        }

        if content is not None:
            payload["data"]["content"] = content
        if name is not None:
            payload["data"]["name"] = name

        logger.debug(f"Updating journal entry: {journal_id}")

        try:
            response = requests.put(url, json=payload, headers=headers, timeout=30)

            if response.status_code != 200:
                logger.error(f"Update failed: {response.status_code}")
                raise RuntimeError(f"Failed to update journal: {response.status_code}")

            result = response.json()
            logger.info(f"Updated journal entry: {journal_id}")
            return result

        except requests.exceptions.RequestException as e:
            logger.error(f"Update request failed: {e}")
            raise RuntimeError(f"Failed to update journal: {e}") from e

    def create_or_update_journal(
        self,
        name: str,
        content: str,
        folder: str = None
    ) -> Dict[str, Any]:
        """
        Create a new journal or update existing one with same name.

        Args:
            name: Name of the journal entry
            content: HTML content for the journal
            folder: Optional folder ID

        Returns:
            Dict containing journal entry data
        """
        existing = self.find_journal_by_name(name)

        if existing:
            logger.info(f"Journal '{name}' exists, updating...")
            return self.update_journal_entry(
                journal_id=existing["_id"],
                content=content
            )
        else:
            logger.info(f"Journal '{name}' not found, creating...")
            return self.create_journal_entry(
                name=name,
                content=content,
                folder=folder
            )
