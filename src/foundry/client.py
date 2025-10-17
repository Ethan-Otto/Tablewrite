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
            self.client_id = os.getenv("FOUNDRY_LOCAL_CLIENT_ID")
            if not self.foundry_url:
                raise ValueError("FOUNDRY_LOCAL_URL not set in environment")
            if not self.api_key:
                raise ValueError("FOUNDRY_LOCAL_API_KEY not set in environment")
            if not self.client_id:
                raise ValueError("FOUNDRY_LOCAL_CLIENT_ID not set in environment")
        elif target == "forge":
            self.foundry_url = os.getenv("FOUNDRY_FORGE_URL")
            self.api_key = os.getenv("FOUNDRY_FORGE_API_KEY")
            self.client_id = os.getenv("FOUNDRY_FORGE_CLIENT_ID")
            if not self.foundry_url:
                raise ValueError("FOUNDRY_FORGE_URL not set in environment")
            if not self.api_key:
                raise ValueError("FOUNDRY_FORGE_API_KEY not set in environment")
            if not self.client_id:
                raise ValueError("FOUNDRY_FORGE_CLIENT_ID not set in environment")
        else:
            raise ValueError(f"Invalid target: {target}. Must be 'local' or 'forge'")

        logger.info(f"Initialized FoundryClient for {target} at {self.foundry_url}")

    def create_journal_entry(
        self,
        name: str,
        pages: list = None,
        content: str = None,
        folder: str = None
    ) -> Dict[str, Any]:
        """
        Create a new journal entry in FoundryVTT.

        Args:
            name: Name of the journal entry
            pages: List of page dicts with 'name' and 'content' keys (preferred)
            content: HTML content for single-page journal (legacy, use pages instead)
            folder: Optional folder ID to organize the journal

        Returns:
            Dict containing created journal entry data

        Raises:
            RuntimeError: If API request fails
            ValueError: If neither pages nor content provided
        """
        url = f"{self.relay_url}/create?clientId={self.client_id}"

        headers = {
            "x-api-key": self.api_key,
            "Content-Type": "application/json"
        }

        # Build pages array
        if pages:
            # Multiple pages provided
            pages_data = [
                {
                    "name": page["name"],
                    "type": "text",
                    "text": {
                        "content": page["content"]
                    }
                }
                for page in pages
            ]
        elif content is not None:
            # Legacy single-page mode
            pages_data = [
                {
                    "name": name,
                    "type": "text",
                    "text": {
                        "content": content
                    }
                }
            ]
        else:
            raise ValueError("Must provide either 'pages' or 'content'")

        payload = {
            "entityType": "JournalEntry",
            "data": {
                "name": name,
                "pages": pages_data
            }
        }

        if folder:
            payload["data"]["folder"] = folder

        page_count = len(pages_data)
        logger.debug(f"Creating journal entry: {name} with {page_count} page(s)")

        try:
            response = requests.post(url, json=payload, headers=headers, timeout=30)

            if response.status_code != 200:
                logger.error(f"Failed to create journal: {response.status_code} - {response.text}")
                raise RuntimeError(
                    f"Failed to create journal entry: {response.status_code} - {response.text}"
                )

            result = response.json()
            # Response format: {"entity": {"_id": "..."}, "uuid": "JournalEntry.xxx"}
            entity_id = result.get('entity', {}).get('_id') or result.get('uuid', 'unknown')
            logger.info(f"Created journal entry: {name} with {page_count} page(s) (ID: {entity_id})")
            return result

        except requests.exceptions.RequestException as e:
            logger.error(f"Request failed: {e}")
            raise RuntimeError(f"Failed to create journal entry: {e}") from e

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
            "clientId": self.client_id,
            "type": "JournalEntry",
            "query": name
        }

        logger.debug(f"Searching for journal: {name}")

        try:
            response = requests.get(url, params=params, headers=headers, timeout=30)

            if response.status_code != 200:
                logger.warning(f"Search failed: {response.status_code} - search not available, will create new journal")
                return None  # Search failed, assume not found

            results = response.json()

            # Check for QuickInsert error (search module not available)
            if isinstance(results, dict) and results.get("error"):
                logger.warning(f"Search error: {results['error']} - will create new journal")
                return None

            # Check for empty results
            if not results or (isinstance(results, dict) and not results.get("results")):
                logger.debug(f"No journal found with name: {name}")
                return None

            # Handle both list and dict response formats
            search_results = results if isinstance(results, list) else results.get("results", [])

            # Return first exact match
            for journal in search_results:
                if journal.get("name") == name:
                    # Search results use 'id' field, normalize to '_id' for consistency
                    if 'id' in journal and '_id' not in journal:
                        journal['_id'] = journal['id']
                    logger.debug(f"Found journal: {name} (ID: {journal.get('_id') or journal.get('id')})")
                    return journal

            return None

        except requests.exceptions.RequestException as e:
            logger.warning(f"Search request failed: {e} - will create new journal")
            return None  # Network error, assume not found

    def update_journal_entry(
        self,
        journal_uuid: str,
        pages: list = None,
        content: str = None,
        name: str = None
    ) -> Dict[str, Any]:
        """
        Update an existing journal entry.

        Args:
            journal_uuid: UUID of the journal entry (format: JournalEntry.{id})
            pages: List of page dicts with 'name' and 'content' keys (preferred)
            content: New HTML content for single page (legacy, use pages instead)
            name: New name (optional)

        Returns:
            Dict containing updated journal entry data

        Raises:
            RuntimeError: If API request fails
        """
        url = f"{self.relay_url}/update?clientId={self.client_id}&uuid={journal_uuid}"

        headers = {
            "x-api-key": self.api_key,
            "Content-Type": "application/json"
        }

        payload = {
            "data": {}
        }

        # Build pages array if content provided
        if pages:
            # Multiple pages provided
            payload["data"]["pages"] = [
                {
                    "name": page["name"],
                    "type": "text",
                    "text": {
                        "content": page["content"]
                    }
                }
                for page in pages
            ]
        elif content is not None:
            # Legacy single-page mode
            payload["data"]["pages"] = [
                {
                    "name": name or "Content",
                    "type": "text",
                    "text": {
                        "content": content
                    }
                }
            ]

        if name is not None:
            payload["data"]["name"] = name

        page_info = f" with {len(pages)} page(s)" if pages else ""
        logger.debug(f"Updating journal entry: {journal_uuid}{page_info}")

        try:
            response = requests.put(url, json=payload, headers=headers, timeout=30)

            if response.status_code != 200:
                logger.error(f"Update failed: {response.status_code} - {response.text}")
                raise RuntimeError(f"Failed to update journal: {response.status_code} - {response.text}")

            result = response.json()
            logger.info(f"Updated journal entry: {journal_uuid}{page_info}")
            return result

        except requests.exceptions.RequestException as e:
            logger.error(f"Update request failed: {e}")
            raise RuntimeError(f"Failed to update journal: {e}") from e

    def delete_journal_entry(self, journal_uuid: str) -> Dict[str, Any]:
        """
        Delete a journal entry.

        Args:
            journal_uuid: UUID of the journal entry (format: JournalEntry.{id})

        Returns:
            Dict with success status

        Raises:
            RuntimeError: If API request fails
        """
        url = f"{self.relay_url}/delete?clientId={self.client_id}&uuid={journal_uuid}"

        headers = {
            "x-api-key": self.api_key,
            "Content-Type": "application/json"
        }

        logger.debug(f"Deleting journal entry: {journal_uuid}")

        try:
            response = requests.delete(url, headers=headers, timeout=30)

            if response.status_code != 200:
                logger.error(f"Delete failed: {response.status_code} - {response.text}")
                raise RuntimeError(f"Failed to delete journal: {response.status_code} - {response.text}")

            result = response.json()
            logger.info(f"Deleted journal entry: {journal_uuid}")
            return result

        except requests.exceptions.RequestException as e:
            logger.error(f"Delete request failed: {e}")
            raise RuntimeError(f"Failed to delete journal: {e}") from e

    def create_or_update_journal(
        self,
        name: str,
        pages: list = None,
        content: str = None,
        folder: str = None
    ) -> Dict[str, Any]:
        """
        Create or update a journal entry.

        Searches for existing journal by name. If found, updates it.
        If not found, creates a new journal entry.

        Args:
            name: Name of the journal entry
            pages: List of page dicts with 'name' and 'content' keys (preferred)
            content: HTML content for single-page journal (legacy, use pages instead)
            folder: Optional folder ID

        Returns:
            Dict containing journal entry data

        Raises:
            ValueError: If neither pages nor content provided
        """
        if not pages and content is None:
            raise ValueError("Must provide either 'pages' or 'content'")

        # Try to find existing journal
        existing = self.find_journal_by_name(name)

        if existing:
            # Extract UUID for update
            # Search results may have 'uuid' field or we construct from 'id'/'_id'
            journal_uuid = existing.get('uuid')
            if not journal_uuid:
                journal_id = existing.get('_id') or existing.get('id')
                if journal_id:
                    journal_uuid = f"JournalEntry.{journal_id}"

            if journal_uuid:
                logger.info(f"Updating existing journal: {name} (UUID: {journal_uuid})")
                return self.update_journal_entry(
                    journal_uuid=journal_uuid,
                    pages=pages,
                    content=content,
                    name=name
                )
            else:
                logger.warning(f"Found journal but no UUID available, creating new: {name}")

        # Create new journal if not found or no UUID
        logger.info(f"Creating new journal entry: {name}")
        return self.create_journal_entry(
            name=name,
            pages=pages,
            content=content,
            folder=folder
        )
